from __future__ import annotations

from typing import Protocol


class BrowserLike(Protocol):
    def get_page_source(self) -> str: ...
    def get_current_url(self) -> str: ...


def _raise_assertion(message: str) -> None:
    """直接抛出 AssertionError，避免 assert_true(False) 产生 'False is not true' 前缀。"""
    raise AssertionError(message)


def _build_haystack(sb: BrowserLike, check_url: bool) -> str:
    haystack = sb.get_page_source()
    if check_url:
        haystack = f"{haystack}\n{sb.get_current_url()}"
    return haystack


def _keyword_check_results(haystack: str, keywords: tuple[str, ...]) -> dict[str, bool]:
    return {keyword: keyword in haystack for keyword in keywords}


def _format_failure_message(
    title: str,
    *,
    expect_label: str,
    expect_value: str,
    current_url: str,
    detail: str,
) -> str:
    """组装单行断言失败信息，避免 pytest 输出重复展开。"""
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
    断言当前页面包含指定关键词。

    - match_all=False：满足任一关键词即可（OR）
    - match_all=True：必须全部满足（AND）
    - check_url=True：同时在页面源码与当前 URL 中查找
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
    if match_all:
        detail = f"缺失关键词: {', '.join(missing)}"
    else:
        detail = f"未命中任一关键词: {keywords_text}"

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
    """断言页面包含任一关键词（OR）。"""
    assert_page_contains(
        sb, *keywords, match_all=False, message=message, check_url=check_url
    )


def assert_page_contains_all(
    sb: BrowserLike,
    *keywords: str,
    message: str | None = None,
    check_url: bool = True,
) -> None:
    """断言页面包含全部关键词（AND）。"""
    assert_page_contains(
        sb, *keywords, match_all=True, message=message, check_url=check_url
    )


def assert_page_not_contains(
    sb: BrowserLike,
    *keywords: str,
    message: str | None = None,
    check_url: bool = True,
) -> None:
    """断言页面不包含给定关键词（任一出现即失败）。"""
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
    """断言当前 URL 包含指定片段。"""
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
    detail = f"URL 未满足{mode}匹配"
    final_message = _format_failure_message(
        title,
        expect_label=f"期望URL片段({mode})",
        expect_value=fragments_text,
        current_url=current_url,
        detail=detail,
    )
    _raise_assertion(final_message)
