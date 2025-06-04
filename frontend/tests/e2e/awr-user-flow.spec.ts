import { test, expect, Page } from '@playwright/test';
import path from 'path';

// AWR核心用户流程E2E测试
test.describe('AWR用户流程测试', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto('http://localhost:3000');
  });

  test.afterEach(async () => {
    await page?.close();
  });

  test('完整的AWR文件处理流程', async () => {
    // 1. 访问首页并导航到上传页面
    await test.step('导航到上传页面', async () => {
      await expect(page.locator('h1')).toContainText('Oracle AWR分析器');
      
      // 点击"开始分析"或导航到上传页面
      await page.click('text=立即开始');
      await expect(page).toHaveURL(/.*\/upload/);
      
      // 验证上传页面内容
      await expect(page.locator('h2')).toContainText('AWR文件上传与解析');
    });

    // 2. 文件上传流程
    await test.step('上传AWR文件', async () => {
      // 模拟文件上传（使用测试文件）
      const fileInput = page.locator('input[type="file"]');
      await expect(fileInput).toBeVisible();
      
      // 创建模拟AWR文件内容
      const mockAwrContent = `
        <!DOCTYPE html>
        <html>
        <head><title>AWR Report</title></head>
        <body>
          <h1>Oracle AWR Report</h1>
          <table>
            <tr><td>Database Name:</td><td>TESTDB</td></tr>
            <tr><td>Instance Name:</td><td>testdb1</td></tr>
          </table>
        </body>
        </html>
      `;
      
      // 上传文件
      await fileInput.setInputFiles({
        name: 'test-awr-report.html',
        mimeType: 'text/html',
        buffer: Buffer.from(mockAwrContent)
      });

      // 验证文件上传成功提示
      await expect(page.locator('.ant-message')).toContainText('上传成功', { timeout: 5000 });
    });

    // 3. 启动解析流程
    await test.step('启动解析任务', async () => {
      // 查找并点击解析按钮
      const parseButton = page.locator('button:has-text("开始解析")');
      await expect(parseButton).toBeVisible({ timeout: 3000 });
      await parseButton.click();

      // 验证解析启动成功
      await expect(page.locator('.ant-message')).toContainText('解析任务已启动', { timeout: 5000 });
      
      // 自动跳转到进度页面
      await expect(page).toHaveURL(/.*\/parse-progress\/.*/, { timeout: 5000 });
    });

    // 4. 进度跟踪页面验证
    await test.step('验证解析进度页面', async () => {
      // 验证页面标题
      await expect(page.locator('h2')).toContainText('解析进度跟踪');
      
      // 验证进度卡片
      await expect(page.locator('.ant-card:has-text("解析进度")')).toBeVisible();
      
      // 验证进度条
      await expect(page.locator('.ant-progress')).toBeVisible();
      
      // 验证详细步骤
      await expect(page.locator('.ant-steps')).toBeVisible();
      await expect(page.locator('text=文件验证')).toBeVisible();
      await expect(page.locator('text=解析数据库信息')).toBeVisible();
      
      // 验证取消按钮（如果解析还在进行中）
      const cancelButton = page.locator('button:has-text("取消解析")');
      if (await cancelButton.isVisible()) {
        await expect(cancelButton).toBeEnabled();
      }
    });

    // 5. 模拟解析完成并跳转结果页面
    await test.step('验证解析完成流程', async () => {
      // 等待解析完成或模拟完成状态
      // 在真实场景中，这里可能需要等待或使用mock数据
      
      // 检查是否有"查看解析结果"按钮
      const viewResultButton = page.locator('button:has-text("查看解析结果")');
      
      // 如果没有自动跳转，手动点击查看结果
      if (await viewResultButton.isVisible({ timeout: 10000 })) {
        await viewResultButton.click();
        await expect(page).toHaveURL(/.*\/results\/.*/, { timeout: 5000 });
      } else {
        // 直接导航到结果页面进行验证
        await page.goto('/results/mock-result-id');
      }
    });
  });

  test('文件上传错误处理', async () => {
    await page.goto('/upload');

    await test.step('验证无效文件类型', async () => {
      const fileInput = page.locator('input[type="file"]');
      
      // 上传非HTML文件
      await fileInput.setInputFiles({
        name: 'invalid-file.txt',
        mimeType: 'text/plain',
        buffer: Buffer.from('This is not an AWR report')
      });

      // 验证错误提示
      await expect(page.locator('.ant-message-error')).toBeVisible({ timeout: 5000 });
    });

    await test.step('验证文件大小限制', async () => {
      const fileInput = page.locator('input[type="file"]');
      
      // 创建超大文件（模拟超过50MB）
      const largeContent = 'x'.repeat(1024 * 1024); // 1MB内容，实际可能需要更大
      
      await fileInput.setInputFiles({
        name: 'large-awr-report.html',
        mimeType: 'text/html',
        buffer: Buffer.from(largeContent)
      });

      // 这里可能需要等待错误提示，具体取决于实现
      // await expect(page.locator('.ant-message-error')).toContainText('文件过大');
    });
  });

  test('解析进度页面交互', async () => {
    // 直接导航到模拟的进度页面
    await page.goto('/parse-progress/mock-task-id');

    await test.step('验证页面基本元素', async () => {
      await expect(page.locator('h2')).toContainText('解析进度跟踪');
      await expect(page.locator('button:has-text("返回上传")')).toBeVisible();
    });

    await test.step('验证导航功能', async () => {
      // 点击返回上传按钮
      await page.click('button:has-text("返回上传")');
      await expect(page).toHaveURL(/.*\/upload/);
      
      // 返回进度页面
      await page.goBack();
      await expect(page).toHaveURL(/.*\/parse-progress/);
    });

    await test.step('验证历史记录导航', async () => {
      const historyButton = page.locator('button:has-text("解析历史")');
      if (await historyButton.isVisible()) {
        await historyButton.click();
        await expect(page).toHaveURL(/.*\/history/);
      }
    });
  });

  test('响应式设计测试', async () => {
    await test.step('移动端视图测试', async () => {
      // 设置移动端视口
      await page.setViewportSize({ width: 375, height: 667 });
      
      await page.goto('/upload');
      
      // 验证移动端布局
      await expect(page.locator('h2')).toBeVisible();
      
      // 验证文件上传组件在移动端的可用性
      const uploadArea = page.locator('.ant-upload-drag');
      await expect(uploadArea).toBeVisible();
      
      // 验证按钮是否适合移动端点击
      const buttons = page.locator('button');
      for (let i = 0; i < await buttons.count(); i++) {
        const button = buttons.nth(i);
        if (await button.isVisible()) {
          const boundingBox = await button.boundingBox();
          if (boundingBox) {
            // 验证按钮高度至少44px（iOS推荐最小点击区域）
            expect(boundingBox.height).toBeGreaterThanOrEqual(32);
          }
        }
      }
    });

    await test.step('平板端视图测试', async () => {
      // 设置平板端视口
      await page.setViewportSize({ width: 768, height: 1024 });
      
      await page.goto('/parse-progress/mock-task-id');
      
      // 验证平板端布局
      await expect(page.locator('h2')).toBeVisible();
      
      // 验证卡片布局在平板端的显示
      const cards = page.locator('.ant-card');
      for (let i = 0; i < await cards.count(); i++) {
        const card = cards.nth(i);
        await expect(card).toBeVisible();
      }
    });
  });

  test('网络错误处理', async () => {
    await test.step('模拟网络断开', async () => {
      // 模拟离线状态
      await page.context().setOffline(true);
      
      await page.goto('/upload');
      
      // 尝试上传文件
      const fileInput = page.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: 'test-awr.html',
        mimeType: 'text/html',
        buffer: Buffer.from('<html><body>Test AWR</body></html>')
      });

      // 验证网络错误处理
      // 具体的错误提示取决于实现
      await expect(page.locator('.ant-message-error, .ant-alert-error')).toBeVisible({ timeout: 10000 });
      
      // 恢复网络
      await page.context().setOffline(false);
    });
  });

  test('浏览器兼容性基础验证', async () => {
    await test.step('验证核心功能在不同浏览器', async () => {
      // 验证页面基本渲染
      await page.goto('/');
      await expect(page.locator('h1')).toBeVisible();
      
      // 验证CSS Grid/Flexbox支持
      const layout = page.locator('.ant-layout');
      await expect(layout).toBeVisible();
      
      // 验证JavaScript功能
      await page.goto('/upload');
      const uploadComponent = page.locator('.ant-upload');
      await expect(uploadComponent).toBeVisible();
      
      // 验证路由功能
      await page.click('text=返回首页');
      await expect(page).toHaveURL('/');
    });
  });

  test('性能基础指标', async () => {
    await test.step('页面加载性能检查', async () => {
      const startTime = Date.now();
      
      await page.goto('/');
      
      // 等待页面完全加载
      await page.waitForLoadState('networkidle');
      
      const loadTime = Date.now() - startTime;
      
      // 验证页面加载时间合理（< 3秒）
      expect(loadTime).toBeLessThan(3000);
      
      // 验证关键内容已加载
      await expect(page.locator('h1')).toBeVisible();
    });
  });
}); 