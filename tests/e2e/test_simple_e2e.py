"""
Oracle AWR分析器 - 简单E2E测试
{{CHENGQI: P1-TE-004 基础测试框架配置 - 2025-06-01 23:45:00 +08:00}}

不依赖Django数据库的简单E2E测试
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
@pytest.mark.no_db
def test_simple_page_load(page: Page):
    """测试简单页面加载"""
    page.goto("https://httpbin.org/html")
    expect(page).to_have_title("Herman Melville - Moby-Dick")


@pytest.mark.e2e
@pytest.mark.no_db
def test_json_api_response(page: Page):
    """测试JSON API响应"""
    page.goto("https://httpbin.org/json")
    expect(page.locator("body")).to_contain_text("slideshow")


@pytest.mark.e2e
@pytest.mark.no_db
def test_form_interaction(page: Page):
    """测试表单交互"""
    page.goto("https://httpbin.org/forms/post")
    
    # 填写表单
    page.fill('input[name="custname"]', "Test User")
    page.fill('input[name="custemail"]', "test@example.com")
    
    # 验证表单填写
    expect(page.locator('input[name="custname"]')).to_have_value("Test User")
    expect(page.locator('input[name="custemail"]')).to_have_value("test@example.com") 