from __future__ import annotations

from typing import Protocol


class BrowserLike(Protocol):
    """
    封装目的:
    - 约束 UI 断言函数对浏览器对象的最小能力要求，降低耦合。

    封装实现:
    - 以 Protocol 定义 get_page_source/get_current_url 两个方法。

    外部接口:
    - 任意对象实现该协议即可被本模块断言函数接收。
    """

    def get_page_source(self) -> str: ...
    def get_current_url(self) -> str: ...


def _raise_assertion(message: str) -> None:
    """
    封装目的:
    - 统一抛出断言异常，保持调用栈入口一致。

    封装实现:
    - 直接抛出 AssertionError。

    外部接口:
    - 入参: message，断言失败文案。
    - 出参: 无；恒抛异常。
    """
    raise AssertionError(message)


def _build_haystack(sb: BrowserLike, check_url: bool) -> str:
    """
    封装目的:
    - 统一构建关键词搜索文本源，支持页面源码和 URL 联合检查。

    封装实现:
    - 默认读取页面源码。
    - check_url=True 时将当前 URL 拼接到文本源中。

    外部接口:
    - 入参: sb（浏览器对象）、check_url（是否纳入 URL）。
    - 出参: 用于匹配的字符串。
    """
    haystack = sb.get_page_source()
    if check_url:
        haystack = f"{haystack}\n{sb.get_current_url()}"
    return haystack


def _keyword_check_results(haystack: str, keywords: tuple[str, ...]) -> dict[str, bool]:
    """
    封装目的:
    - 生成关键词命中结果映射，便于统一处理 all/any 判定与报错信息。

    封装实现:
    - 使用字典推导逐个判断关键词是否存在于文本源。

    外部接口:
    - 入参: haystack、keywords。
    - 出参: {关键词: 是否命中} 字典。
    """
    return {keyword: keyword in haystack for keyword in keywords}


def _format_failure_message(
    title: str,
    *,
    expect_label: str,
    expect_value: str,
    current_url: str,
    detail: str,
) -> str:
    """
    封装目的:
    - 统一断言失败文案格式，确保报告输出结构一致可读。

    封装实现:
    - 拼装标题、期望值、当前 URL 与详细说明信息。

    外部接口:
    - 入参: 标题、期望标签/值、当前 URL、详细说明。
    - 出参: 格式化后的断言失败字符串。
    """
    return (
        f"{title} \n {expect_label}: [{expect_value}] \n "
        f"当前URL: {current_url} \n {detail}"
    )


def assert_page_contains(
    sb: BrowserLike,
    *keywords: str,
    match_all: bool = False,
    message: str | None = None,
    check_url: bool = True,
) -> None:
    """
    封装目的:
    - 断言页面内容（可选含 URL）包含指定关键词，支持“任一”与“全部”两种模式。

    封装实现:
    - 构建文本源并计算关键词命中结果。
    - 按 match_all 执行 all/any 规则判定。
    - 失败时生成结构化错误文案并抛出 AssertionError。

    外部接口:
    - 入参: sb、keywords、match_all、message、check_url。
    - 出参: 无；失败时抛 AssertionError，keywords 为空时抛 ValueError。
    """
    if not keywords:
        raise ValueError("assert_page_contains 至少需要一个关键词参数")

    haystack = _build_haystack(sb, check_url)
    results = _keyword_check_results(haystack, keywords)
    passed = all(results.values()) if match_all else any(results.values())
    if passed:
        return

    mode = "全部" if match_all else "任一"
    keywords_text = ", ".join(keywords)
    current_url = sb.get_current_url()
    missing = [keyword for keyword, found in results.items() if not found]
    detail = (
        f"缺失关键词: {', '.join(missing)}"
        if match_all
        else f"未命中任一关键词: {keywords_text}"
    )

    title = message or f"【页面内容断言失败】期望包含{mode}关键词"
    final_message = _format_failure_message(
        title,
        expect_label=f"期望关键词({mode})",
        expect_value=keywords_text,
        current_url=current_url,
        detail=detail,
    )
    _raise_assertion(final_message)


def assert_page_contains_any(
    sb: BrowserLike,
    *keywords: str,
    message: str | None = None,
    check_url: bool = True,
) -> None:
    """
    封装目的:
    - 提供“页面包含任一关键词”的语义化快捷断言。

    封装实现:
    - 转调 assert_page_contains(match_all=False)。

    外部接口:
    - 入参: sb、keywords、message、check_url。
    - 出参: 无；失败抛 AssertionError。
    """
    assert_page_contains(sb, *keywords, match_all=False, message=message, check_url=check_url)


def assert_page_contains_all(
    sb: BrowserLike,
    *keywords: str,
    message: str | None = None,
    check_url: bool = True,
) -> None:
    """
    封装目的:
    - 提供“页面包含全部关键词”的语义化快捷断言。

    封装实现:
    - 转调 assert_page_contains(match_all=True)。

    外部接口:
    - 入参: sb、keywords、message、check_url。
    - 出参: 无；失败抛 AssertionError。
    """
    assert_page_contains(sb, *keywords, match_all=True, message=message, check_url=check_url)


def assert_page_not_contains(
    sb: BrowserLike,
    *keywords: str,
    message: str | None = None,
    check_url: bool = True,
) -> None:
    """
    封装目的:
    - 断言页面内容不包含指定关键词，支持多关键词批量检查。

    封装实现:
    - 构建文本源后筛选命中关键词列表。
    - 仅当存在命中项时构造失败信息并抛异常。

    外部接口:
    - 入参: sb、keywords、message、check_url。
    - 出参: 无；失败抛 AssertionError，keywords 为空时抛 ValueError。
    """
    if not keywords:
        raise ValueError("assert_page_not_contains 至少需要一个关键词参数")

    haystack = _build_haystack(sb, check_url)
    hit = [keyword for keyword in keywords if keyword in haystack]
    if not hit:
        return

    keywords_text = ", ".join(hit)
    current_url = sb.get_current_url()
    title = message or "【页面内容断言失败】页面不应包含以下关键词"
    final_message = _format_failure_message(
        title,
        expect_label="不应出现关键词",
        expect_value=keywords_text,
        current_url=current_url,
        detail=f"不应出现但已出现: {keywords_text}",
    )
    _raise_assertion(final_message)


def assert_url_contains(
    sb: BrowserLike,
    *fragments: str,
    match_all: bool = False,
    message: str | None = None,
) -> None:
    """
    封装目的:
    - 断言当前 URL 包含指定片段，支持“任一”与“全部”匹配策略。

    封装实现:
    - 在当前 URL 上计算片段命中情况。
    - 根据 match_all 判定是否通过，失败时输出统一错误文案。

    外部接口:
    - 入参: sb、fragments、match_all、message。
    - 出参: 无；失败抛 AssertionError，fragments 为空时抛 ValueError。
    """
    if not fragments:
        raise ValueError("assert_url_contains 至少需要一个 URL 片段参数")

    current_url = sb.get_current_url()
    results = {fragment: fragment in current_url for fragment in fragments}
    passed = all(results.values()) if match_all else any(results.values())
    if passed:
        return

    mode = "全部" if match_all else "任一"
    fragments_text = ", ".join(fragments)
    title = message or f"【URL 断言失败】期望 URL 包含{mode}片段"
    final_message = _format_failure_message(
        title,
        expect_label=f"期望URL片段({mode})",
        expect_value=fragments_text,
        current_url=current_url,
        detail=f"URL 未满足{mode}匹配",
    )
    _raise_assertion(final_message)
