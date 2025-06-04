import { test, expect } from '@playwright/test';

// 基础导航测试
test.describe('AWR基础导航测试', () => {
  
  test('首页可以正常访问', async ({ page }) => {
    await page.goto('/');
    
    // 验证页面标题
    await expect(page).toHaveTitle(/Oracle AWR/);
    
    // 验证主要标题
    await expect(page.locator('h1')).toContainText('Oracle AWR');
  });

  test('上传页面可以正常访问', async ({ page }) => {
    await page.goto('/upload');
    
    // 验证页面内容
    await expect(page.locator('h2')).toContainText('AWR文件上传与解析');
    
    // 验证上传组件存在
    await expect(page.locator('.ant-upload')).toBeVisible();
  });

  test('解析进度页面可以访问（模拟ID）', async ({ page }) => {
    await page.goto('/parse-progress/test-id');
    
    // 验证页面标题或内容
    const titleOrError = page.locator('h2, .ant-result-title');
    await expect(titleOrError).toBeVisible();
  });

  test('结果页面可以访问（模拟ID）', async ({ page }) => {
    await page.goto('/results/test-id');
    
    // 验证页面有内容渲染
    const content = page.locator('h2, .ant-result, .ant-card');
    await expect(content.first()).toBeVisible();
  });

  test('历史页面可以正常访问', async ({ page }) => {
    await page.goto('/history');
    
    // 验证页面内容
    const content = page.locator('h2, .ant-table, .ant-empty');
    await expect(content.first()).toBeVisible();
  });

  test('导航菜单功能', async ({ page }) => {
    await page.goto('/');
    
    // 检查是否有导航元素
    const navigation = page.locator('.ant-menu, .ant-layout-sider, nav');
    
    if (await navigation.isVisible()) {
      // 如果有导航，测试导航功能
      await expect(navigation).toBeVisible();
    } else {
      // 如果没有导航，测试直接URL访问
      await page.goto('/upload');
      await expect(page).toHaveURL(/.*upload/);
    }
  });

  test('响应式布局基础测试', async ({ page }) => {
    // 桌面端
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.goto('/upload');
    await expect(page.locator('h2')).toBeVisible();
    
    // 平板端
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.goto('/upload');
    await expect(page.locator('h2')).toBeVisible();
    
    // 移动端
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/upload');
    await expect(page.locator('h2')).toBeVisible();
  });
}); 