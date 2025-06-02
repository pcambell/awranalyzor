"""
Oracle AWR分析器 - 纯Playwright E2E测试
{{CHENGQI: P1-TE-004 基础测试框架配置 - 2025-06-01 23:45:00 +08:00}}

纯Playwright测试，不依赖Django
"""
import pytest
from playwright.sync_api import Page, expect


# 使用pytest.mark.no_db来避免数据库问题
pytestmark = [pytest.mark.no_db]


def test_basic_playwright_functionality(page: Page):
    """测试基础Playwright功能"""
    page.goto("https://httpbin.org/html")
    # httpbin.org/html 页面没有title，只检查h1标签
    expect(page.locator("h1")).to_contain_text("Herman Melville - Moby-Dick")


def test_json_response(page: Page):
    """测试JSON响应"""
    page.goto("https://httpbin.org/json")
    expect(page.locator("body")).to_contain_text("slideshow")


def test_form_filling(page: Page):
    """测试表单填写"""
    page.goto("https://httpbin.org/forms/post")
    
    # 填写表单
    page.fill('input[name="custname"]', "Test User")
    page.fill('input[name="custemail"]', "test@example.com")
    
    # 验证表单填写
    expect(page.locator('input[name="custname"]')).to_have_value("Test User")
    expect(page.locator('input[name="custemail"]')).to_have_value("test@example.com")


def test_navigation(page: Page):
    """测试页面导航"""
    page.goto("https://httpbin.org/")
    
    # 验证主页加载成功
    expect(page).to_have_title("httpbin.org")
    
    # 直接导航到html页面而不是点击链接
    page.goto("https://httpbin.org/html")
    expect(page).to_have_url("https://httpbin.org/html")
    expect(page.locator("h1")).to_be_visible()


def test_screenshot(page: Page):
    """测试截图功能"""
    page.goto("https://httpbin.org/html")
    screenshot = page.screenshot()
    assert len(screenshot) > 0


def test_mobile_viewport(page: Page):
    """测试移动端视口"""
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto("https://httpbin.org/html")
    expect(page.locator("h1")).to_be_visible()


def test_json_api_endpoint(page: Page):
    """测试JSON API端点"""
    page.goto("https://httpbin.org/get")
    # 验证JSON响应格式
    expect(page.locator("body")).to_contain_text('"url": "https://httpbin.org/get"')


def test_status_code_endpoint(page: Page):
    """测试状态码端点"""
    page.goto("https://httpbin.org/status/200")
    # 200状态码应该正常加载
    assert page.url == "https://httpbin.org/status/200"


def test_user_agent_detection(page: Page):
    """测试User-Agent检测"""
    page.goto("https://httpbin.org/user-agent")
    # 页面应该显示User-Agent信息
    expect(page.locator("body")).to_contain_text("user-agent") 