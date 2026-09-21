"""再利用可能なファイル整理ロジック。

このモジュールは UI を持たず、CLI や将来の GUI から呼び出すためのものです。
"""

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

    return [item for item in target_folder.iterdir() if item.is_file() and item.suffix]


def create_organization_plan(folder: PathLike) -> PlanResult:
    """ファイルを移動せずに、整理予定を作成する。"""

    result = PlanResult()
    target_folder = Path(folder)

    try:
        files = get_target_files(target_folder)
    except (OSError, ValueError) as error:
        result.failures.append(FileFailure(message=str(error), source=target_folder))
        return result

    # 同じ実行内で予定済みの移動先も予約し、上書きを防ぐ。
    reserved_destinations = set()
    for item in files:
        try:
            extension = item.suffix.lower()
            destination_folder = target_folder / extension[1:]
            destination = _make_unique_destination(item, destination_folder, reserved_destinations)
            reserved_destinations.add(destination)
            result.plans.append(
                OrganizationPlan(source=item, destination=destination, extension=extension)
            )
        except OSError as error:
            result.failures.append(FileFailure(message=str(error), source=item))

    return result


def execute_organization_plan(plan_result: PlanResult) -> OrganizationResult:
    """作成済みの整理予定を実行し、各ファイルの成否を返す。"""

    result = OrganizationResult(failed_files=list(plan_result.failures))

    for plan in plan_result.plans:
        try:
            if not plan.source.is_file():
                raise FileNotFoundError("移動元のファイルが存在しません")

            plan.destination.parent.mkdir(parents=True, exist_ok=True)

            # 計画作成後に同名ファイルが追加された場合にも上書きしない。
            if plan.destination.exists():
                raise FileExistsError("移動先に同名のファイルが存在します")

            plan.source.rename(plan.destination)
            result.successful_files.append(plan)
        except OSError as error:
            result.failed_files.append(
                FileFailure(message=str(error), source=plan.source, destination=plan.destination)
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
    while destination.exists() or destination in reserved_destinations:
        destination = destination_folder / f"{source.stem}_{number}{source.suffix}"
        number += 1
    return destination
