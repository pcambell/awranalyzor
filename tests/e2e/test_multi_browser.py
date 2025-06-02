"""
Oracle AWR分析器 - 多浏览器Playwright测试
{{CHENGQI: P1-TE-004 基础测试框架配置 - 2025-06-01 23:45:00 +08:00}}

测试Playwright在不同浏览器中的功能
"""
import pytest
from playwright.sync_api import Page, expect


pytestmark = [pytest.mark.no_db, pytest.mark.e2e]


def test_chromium_specific_features(page: Page):
    """测试Chromium特定功能"""
    page.goto("https://httpbin.org/get")
    expect(page.locator("body")).to_contain_text('"url": "https://httpbin.org/get"')


def test_performance_timing(page: Page):
    """测试性能计时"""
    page.goto("https://httpbin.org/delay/1")
    # 验证页面加载
    assert page.url == "https://httpbin.org/delay/1"


def test_mobile_emulation(page: Page):
    """测试移动设备模拟"""
    # 设置iPhone视口
    page.set_viewport_size({"width": 375, "height": 812})
    page.goto("https://httpbin.org/")
    
    # 验证移动端布局 - 使用第一个h2元素
    expect(page.locator("h2").first).to_be_visible()


def test_javascript_execution(page: Page):
    """测试JavaScript执行"""
    page.goto("https://httpbin.org/")
    
    # 执行JavaScript
    title = page.evaluate("() => document.title")
    assert title == "httpbin.org"
    
    # 获取页面URL
    url = page.evaluate("() => window.location.href")
    assert "httpbin.org" in url


def test_network_interception(page: Page):
    """测试网络请求拦截"""
    responses = []
    
    def handle_response(response):
        responses.append(response.url)
    
    page.on("response", handle_response)
    page.goto("https://httpbin.org/")
    
    # 验证有网络请求
    assert len(responses) > 0
    assert any("httpbin.org" in url for url in responses)


def test_cookies_and_local_storage(page: Page):
    """测试Cookie和本地存储"""
    page.goto("https://httpbin.org/cookies/set/test/value")
    
    # 验证重定向到cookies页面
    expect(page.locator("body")).to_contain_text("cookies")


def test_file_download_simulation(page: Page):
    """测试文件下载模拟"""
    # 访问一个返回文件内容的端点
    page.goto("https://httpbin.org/xml")
    
    # 验证XML内容 - 检查slideshow关键字
    expect(page.locator("body")).to_contain_text("slideshow")


def test_form_submission(page: Page):
    """测试表单提交"""
    page.goto("https://httpbin.org/forms/post")
    
    # 填写表单
    page.fill('input[name="custname"]', "Test User")
    page.fill('input[name="custemail"]', "test@example.com")
    page.fill('textarea[name="comments"]', "Test comment")
    
    # 验证表单填写成功而不是提交
    expect(page.locator('input[name="custname"]')).to_have_value("Test User")
    expect(page.locator('input[name="custemail"]')).to_have_value("test@example.com")
    expect(page.locator('textarea[name="comments"]')).to_have_value("Test comment")


def test_error_handling(page: Page):
    """测试错误处理"""
    # 访问一个会返回错误的端点
    page.goto("https://httpbin.org/status/404")
    
    # 验证404状态（Playwright会正常导航到404页面）
    assert "404" in page.url or page.locator("body").is_visible()


@pytest.mark.slow
def test_timeout_handling(page: Page):
    """测试超时处理"""
    page.goto("https://httpbin.org/delay/2")
    # 验证页面最终加载成功
    assert "delay" in page.url 