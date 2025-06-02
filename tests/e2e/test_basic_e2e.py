"""
Oracle AWR分析器 - 基础E2E测试
{{CHENGQI: P1-TE-004 基础测试框架配置 - 2025-06-01 23:45:00 +08:00}}

验证Playwright E2E测试环境配置
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
def test_basic_page_load(page: Page):
    """测试基础页面加载"""
    # 访问一个简单的页面
    page.goto("https://httpbin.org/html")
    
    # 验证页面标题
    expect(page).to_have_title("Herman Melville - Moby-Dick")
    
    # 验证页面内容
    expect(page.locator("h1")).to_contain_text("Herman Melville - Moby-Dick")


@pytest.mark.e2e
def test_form_interaction(page: Page):
    """测试表单交互"""
    # 访问httpbin的表单页面
    page.goto("https://httpbin.org/forms/post")
    
    # 填写表单
    page.fill('input[name="custname"]', "Test User")
    page.fill('input[name="custtel"]', "1234567890")
    page.fill('input[name="custemail"]', "test@example.com")
    page.select_option('select[name="size"]', "medium")
    
    # 验证表单填写
    expect(page.locator('input[name="custname"]')).to_have_value("Test User")
    expect(page.locator('input[name="custemail"]')).to_have_value("test@example.com")


@pytest.mark.e2e
def test_api_response(page: Page):
    """测试API响应页面"""
    # 访问JSON API
    page.goto("https://httpbin.org/json")
    
    # 验证JSON内容显示
    expect(page.locator("body")).to_contain_text("slideshow")
    expect(page.locator("body")).to_contain_text("title")


@pytest.mark.e2e
@pytest.mark.slow
def test_navigation(page: Page):
    """测试页面导航"""
    # 访问主页
    page.goto("https://httpbin.org/")
    
    # 点击链接
    page.click('a[href="/html"]')
    
    # 验证导航成功
    expect(page).to_have_url("https://httpbin.org/html")
    expect(page.locator("h1")).to_be_visible()


@pytest.mark.e2e
def test_user_agent_page(page: Page):
    """测试用户代理页面"""
    page.goto("https://httpbin.org/user-agent")
    
    # 验证用户代理信息显示
    expect(page.locator("body")).to_contain_text("user-agent")


# 测试移动端视口（如果需要）
@pytest.mark.e2e
def test_mobile_viewport(page: Page):
    """测试移动端视口"""
    # 设置移动端视口
    page.set_viewport_size({"width": 375, "height": 667})
    
    page.goto("https://httpbin.org/html")
    
    # 验证页面在移动端正常显示
    expect(page.locator("h1")).to_be_visible()


# 测试截图功能
@pytest.mark.e2e
def test_screenshot_capability(page: Page):
    """测试截图功能"""
    page.goto("https://httpbin.org/html")
    
    # 截图（保存到临时位置）
    screenshot = page.screenshot()
    assert len(screenshot) > 0  # 验证截图不为空


# 测试等待和超时
@pytest.mark.e2e
def test_wait_and_timeout(page: Page):
    """测试等待和超时机制"""
    page.goto("https://httpbin.org/delay/1")
    
    # 等待页面加载完成
    expect(page.locator("body")).to_contain_text("origin", timeout=5000)


# 测试错误处理
@pytest.mark.e2e
def test_error_handling(page: Page):
    """测试错误处理"""
    # 访问不存在的页面
    response = page.goto("https://httpbin.org/status/404")
    assert response.status == 404


# 跳过测试示例
@pytest.mark.e2e
@pytest.mark.skip(reason="示例跳过测试")
def test_skipped_example(page: Page):
    """这个测试会被跳过"""
    pass


# 条件跳过测试
@pytest.mark.e2e
@pytest.mark.skipif(True, reason="条件跳过示例")
def test_conditional_skip(page: Page):
    """条件跳过的测试"""
    pass 