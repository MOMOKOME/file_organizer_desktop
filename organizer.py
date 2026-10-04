"""再利用可能なファイル整理ロジック。

このモジュールは UI を持たず、CLI や将来の GUI から呼び出すためのものです。
"""

import logging
import os

from organization_rules import normalize_options, destination_category

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union


PathLike = Union[str, Path]


@dataclass(frozen=True)
class OrganizationPlan:
    """1 ファイルを整理するための、変更前に作成する予定。"""

    source: Path
    destination: Path
    extension: str
    identity: Optional[tuple] = None


@dataclass(frozen=True)
class FileFailure:
    """計画作成または整理処理で発生した 1 件分の失敗情報。"""

    message: str
    source: Optional[Path] = None
    destination: Optional[Path] = None


@dataclass
class PlanResult:
    """整理予定の作成結果。予定の作成時点ではファイルを変更しない。"""

    plans: List[OrganizationPlan] = field(default_factory=list)
    failures: List[FileFailure] = field(default_factory=list)
    excluded_count: int = 0


@dataclass
class OrganizationResult:
    """整理の実行結果。GUI はこのデータをそのまま表示に利用できる。"""

    successful_files: List[OrganizationPlan] = field(default_factory=list)
    failed_files: List[FileFailure] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return len(self.successful_files)

    @property
    def failure_count(self) -> int:
        return len(self.failed_files)


def get_target_files(folder: PathLike) -> List[Path]:
    """指定フォルダ直下の、拡張子を持つ通常ファイルだけを返す。

    不正なフォルダや読み取りエラーは OSError / ValueError として呼び出し元へ通知する。
    """

    target_folder = Path(folder)
    if not target_folder.exists():
        raise ValueError("そのフォルダは存在しません")
    if not target_folder.is_dir():
        raise ValueError("指定された場所はフォルダではありません")

    return [item for item in target_folder.iterdir() if item.is_file() and item.suffix and not item.is_symlink()]


def create_organization_plan(folder: PathLike, rule="extension", excluded_extensions=None) -> PlanResult:
    """ファイルを移動せずに、整理予定を作成する。"""

    options = normalize_options(rule, excluded_extensions)
    result = PlanResult()
    target_folder = Path(folder)

    try:
        files = get_target_files(target_folder)
    except (OSError, ValueError) as error:
        result.failures.append(FileFailure(
            message=str(error) if isinstance(error, ValueError) else friendly_error(error),
            source=target_folder))
        return result

    # 同じ実行内で予定済みの移動先も予約し、上書きを防ぐ。
    reserved_destinations = set()
    for item in files:
        try:
            extension = item.suffix.lower()
            if extension in options["excluded_extensions"]:
                result.excluded_count += 1
                continue
            destination_folder = target_folder / (
                extension[1:] if rule == "extension" else destination_category(extension)
            )
            destination = _make_unique_destination(item, destination_folder, reserved_destinations)
            reserved_destinations.add(destination)
            result.plans.append(
                OrganizationPlan(source=item, destination=destination, extension=extension,
                                 identity=_identity(item))
            )
        except OSError as error:
            result.failures.append(FileFailure(message=friendly_error(error), source=item))

    return result


def execute_organization_plan(plan_result: PlanResult) -> OrganizationResult:
    """作成済みの整理予定を実行し、各ファイルの成否を返す。"""

    result = OrganizationResult(failed_files=list(plan_result.failures))

    for plan in plan_result.plans:
        try:
            if plan.identity is not None and _identity(plan.source) != plan.identity:
                raise OSError("Source changed after preview")
            if plan.source.is_symlink() or not plan.source.is_file():
                raise FileNotFoundError("移動元のファイルが存在しません")

            if plan.source.parent.resolve() != Path(os.path.abspath(plan.source.parent)):
                raise OSError("Unsafe source folder")
            if plan.destination.parent.resolve() != Path(os.path.abspath(plan.destination.parent)):
                raise OSError("Unsafe destination folder")
            plan.destination.parent.mkdir(parents=True, exist_ok=True)

            # 計画作成後に同名ファイルが追加された場合にも上書きしない。
            if os.path.lexists(plan.destination):
                raise FileExistsError("移動先に同名のファイルが存在します")

            move_without_overwrite(plan.source, plan.destination)
            result.successful_files.append(plan)
        except OSError as error:
            result.failed_files.append(
                FileFailure(message=friendly_error(error), source=plan.source, destination=plan.destination)
            )

    return result


def organize_folder(folder: PathLike) -> OrganizationResult:
    """予定作成から実行までを行う、CLI・GUI向けの便利な入口。"""

    return execute_organization_plan(create_organization_plan(folder))


def _make_unique_destination(
    source: Path, destination_folder: Path, reserved_destinations: set
) -> Path:
    """既存ファイルと予定済みファイルを避けた移動先パスを返す。"""

    destination = destination_folder / source.name
    number = 1
    while os.path.lexists(destination) or destination in reserved_destinations:
        destination = destination_folder / f"{source.stem}_{number}{source.suffix}"
        number += 1
    return destination


def friendly_error(error):
    logging.getLogger(__name__).warning("File operation failed: %s", error)
    if isinstance(error, PermissionError):
        return "このファイルを移動する権限がありません。別のアプリで開かれていないか確認してください。"
    if isinstance(error, FileExistsError):
        return "移動先に同名のファイルがあります。上書きせずスキップしました。"
    if isinstance(error, FileNotFoundError):
        return "ファイルが見つかりません。移動や名前変更がされていないか確認してください。"
    return "ファイルやフォルダが変更されたか、移動できません。場所・権限・空き容量を確認してください。"


def _identity(path):
    stat = path.stat(follow_symlinks=False)
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


def move_without_overwrite(source, destination):
    """Same-volume move with an exclusive destination, including concurrent collisions."""
    if os.name == "nt":
        # Windows rename fails atomically if the destination already exists.
        source.rename(destination)
    else:
        # link() creates exclusively; unsupported filesystems fail safely.
        os.link(source, destination, follow_symlinks=False)
        source.unlink()
