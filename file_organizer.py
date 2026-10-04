"""file_organizer の CLI 入口。"""

from organizer_service import organize_with_history as organize_folder


def main() -> None:
    """入力を受け取り、整理結果をコンソールに表示する。"""

    folder_path = input("整理したいフォルダを入力してください：")
    result = organize_folder(folder_path)

    for plan in result.successful_files:
        print(plan.source.name, "→", plan.destination)

    for failure in result.failed_files:
        source = failure.source if failure.source is not None else "対象フォルダ"
        print(f"エラー: {source}: {failure.message}")

    print()
    print(f"整理完了！{result.success_count}個のファイルを整理しました。")
    if result.failure_count:
        print(f"失敗: {result.failure_count}件")


if __name__ == "__main__":
    main()
