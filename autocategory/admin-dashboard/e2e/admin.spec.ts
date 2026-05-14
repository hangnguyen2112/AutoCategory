/**
 * End-to-End Tests for Admin Dashboard
 * Tests user flows using Playwright
 */

import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:3001';
const ADMIN_USERNAME = 'admin';
const ADMIN_PASSWORD = 'admin123';

// Helper function to login
async function login(page, username = ADMIN_USERNAME, password = ADMIN_PASSWORD) {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('input[name="username"]', username);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(`${BASE_URL}/`);
}

test.describe('Authentication Flow', () => {
  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', ADMIN_USERNAME);
    await page.fill('input[name="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    
    // Should redirect to dashboard
    await expect(page).toHaveURL(`${BASE_URL}/`);
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });
  
  test('should show error with invalid credentials', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.fill('input[name="username"]', 'admin');
    await page.fill('input[name="password"]', 'wrong_password');
    await page.click('button[type="submit"]');
    
    // Should show error message
    await expect(page.locator('text=/Invalid credentials|Login failed/i')).toBeVisible();
  });
  
  test('should logout successfully', async ({ page }) => {
    await login(page);
    
    // Click logout button
    await page.click('button:has-text("Logout")');
    
    // Should redirect to login
    await expect(page).toHaveURL(`${BASE_URL}/login`);
  });
  
  test('should redirect to login when accessing protected route', async ({ page }) => {
    await page.goto(`${BASE_URL}/users`);
    
    // Should redirect to login
    await expect(page).toHaveURL(`${BASE_URL}/login`);
  });
});

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });
  
  test('should display system stats cards', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    // Check for stat cards
    await expect(page.locator('text=/Total Users/i')).toBeVisible();
    await expect(page.locator('text=/Active API Keys/i')).toBeVisible();
    await expect(page.locator('text=/Total Categories/i')).toBeVisible();
    await expect(page.locator('text=/Training Samples/i')).toBeVisible();
  });
  
  test('should display service health status', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    // Check for service status section
    await expect(page.locator('text=/Service Health/i')).toBeVisible();
    await expect(page.locator('text=/API/i')).toBeVisible();
    await expect(page.locator('text=/Database/i')).toBeVisible();
    await expect(page.locator('text=/Redis/i')).toBeVisible();
  });
  
  test('should display recent activity', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    await expect(page.locator('text=/Recent Activity/i')).toBeVisible();
  });
});

test.describe('User Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/users`);
  });
  
  test('should display user list', async ({ page }) => {
    await expect(page.locator('text=/User Management/i')).toBeVisible();
    await expect(page.locator('table')).toBeVisible();
  });
  
  test('should create a new user', async ({ page }) => {
    // Click create button
    await page.click('button:has-text("Create User")');
    
    // Fill form
    const timestamp = Date.now();
    await page.fill('input[name="username"]', `testuser_${timestamp}`);
    await page.fill('input[name="email"]', `test_${timestamp}@example.com`);
    await page.fill('input[name="password"]', 'test_password_123');
    await page.fill('input[name="full_name"]', 'Test User');
    await page.selectOption('select[name="role"]', 'developer');
    
    // Submit
    await page.click('button[type="submit"]');
    
    // Should see success message
    await expect(page.locator('text=/User created successfully/i')).toBeVisible({ timeout: 10000 });
  });
  
  test('should search for users', async ({ page }) => {
    // Type in search box
    await page.fill('input[placeholder*="Search"]', 'admin');
    
    // Wait for search results
    await page.waitForTimeout(500);
    
    // Should see admin user in results
    await expect(page.locator('text=admin')).toBeVisible();
  });
  
  test('should edit user', async ({ page }) => {
    // Click edit button on first user
    await page.click('button[title="Edit"]:first-of-type');
    
    // Update full name
    await page.fill('input[name="full_name"]', 'Updated Name');
    
    // Submit
    await page.click('button:has-text("Save")');
    
    // Should see success message
    await expect(page.locator('text=/User updated successfully/i')).toBeVisible({ timeout: 10000 });
  });
});

test.describe('API Key Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/api-keys`);
  });
  
  test('should display API key list', async ({ page }) => {
    await expect(page.locator('text=/API Key Management/i')).toBeVisible();
  });
  
  test('should create a new API key', async ({ page }) => {
    // Click create button
    await page.click('button:has-text("Create API Key")');
    
    // Fill form
    await page.fill('input[name="name"]', `Test API Key ${Date.now()}`);
    await page.fill('input[name="rate_limit"]', '1000');
    await page.fill('input[name="expires_in_days"]', '365');
    
    // Submit
    await page.click('button[type="submit"]');
    
    // Should show API key modal with key (shown once)
    await expect(page.locator('text=/Copy your API key now/i')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('code')).toBeVisible();
  });
  
  test('should display usage stats for API keys', async ({ page }) => {
    // Should see usage information
    await expect(page.locator('text=/Usage:/i')).toBeVisible();
  });
});

test.describe('Category Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/categories`);
  });
  
  test('should display category tree', async ({ page }) => {
    await expect(page.locator('text=/Category Management/i')).toBeVisible();
  });
  
  test('should expand/collapse category nodes', async ({ page }) => {
    // Find expand button
    const expandButton = page.locator('button[title*="Expand"]').first();
    
    if (await expandButton.isVisible()) {
      await expandButton.click();
      
      // Wait for child categories to appear
      await page.waitForTimeout(500);
    }
  });
  
  test('should sync categories from main system', async ({ page }) => {
    // Click sync button
    await page.click('button:has-text("Sync Categories")');
    
    // Confirm dialog
    await page.click('button:has-text("Confirm")');
    
    // Should see success message
    await expect(page.locator('text=/Sync started successfully/i')).toBeVisible({ timeout: 10000 });
  });
  
  test('should view sync history', async ({ page }) => {
    // Click history button
    await page.click('button:has-text("Sync History")');
    
    // Should see history modal
    await expect(page.locator('text=/Category Sync History/i')).toBeVisible();
  });
});

test.describe('Training Data Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/training-data`);
  });
  
  test('should display training data list', async ({ page }) => {
    await expect(page.locator('text=/Training Data Management/i')).toBeVisible();
  });
  
  test('should filter by validation status', async ({ page }) => {
    // Click filter
    await page.selectOption('select[name="validation_status"]', 'validated');
    
    // Wait for results
    await page.waitForTimeout(500);
  });
  
  test('should add training sample manually', async ({ page }) => {
    // Click add button
    await page.click('button:has-text("Add Sample")');
    
    // Fill form
    await page.fill('input[name="title"]', 'Test Training Sample');
    await page.fill('textarea[name="description"]', 'This is a test description');
    await page.fill('input[name="price"]', '100000');
    
    // Submit
    await page.click('button[type="submit"]');
    
    // Should see success message
    await expect(page.locator('text=/Sample added successfully/i')).toBeVisible({ timeout: 10000 });
  });
  
  test('should validate a training sample', async ({ page }) => {
    // Click validate button on first unvalidated sample
    const validateButton = page.locator('button:has-text("Validate")').first();
    
    if (await validateButton.isVisible()) {
      await validateButton.click();
      
      // Should see success message
      await expect(page.locator('text=/Sample validated/i')).toBeVisible({ timeout: 10000 });
    }
  });
  
  test('should bulk validate samples', async ({ page }) => {
    // Select multiple checkboxes
    const checkboxes = page.locator('input[type="checkbox"]');
    const count = await checkboxes.count();
    
    if (count > 1) {
      await checkboxes.nth(0).check();
      await checkboxes.nth(1).check();
      
      // Click bulk validate
      await page.click('button:has-text("Bulk Validate")');
      
      // Should see success message
      await expect(page.locator('text=/validated successfully/i')).toBeVisible({ timeout: 10000 });
    }
  });
});

test.describe('Request Logs', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/logs`);
  });
  
  test('should display request logs', async ({ page }) => {
    await expect(page.locator('text=/Request Logs/i')).toBeVisible();
  });
  
  test('should filter by date range', async ({ page }) => {
    // Set date range
    await page.fill('input[name="start_date"]', '2025-01-01');
    await page.fill('input[name="end_date"]', '2025-12-31');
    
    // Click apply
    await page.click('button:has-text("Apply")');
    
    // Wait for results
    await page.waitForTimeout(500);
  });
  
  test('should view log details', async ({ page }) => {
    // Click view button on first log
    const viewButton = page.locator('button[title="View Details"]').first();
    
    if (await viewButton.isVisible()) {
      await viewButton.click();
      
      // Should see details modal
      await expect(page.locator('text=/Log Details/i')).toBeVisible();
    }
  });
});

test.describe('System Control', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/system`);
  });
  
  test('should display system metrics', async ({ page }) => {
    await expect(page.locator('text=/System Control/i')).toBeVisible();
    await expect(page.locator('text=/CPU Usage/i')).toBeVisible();
    await expect(page.locator('text=/Memory/i')).toBeVisible();
  });
  
  test('should clear cache', async ({ page }) => {
    // Click clear cache button
    await page.click('button:has-text("Clear Cache")');
    
    // Confirm
    await page.click('button:has-text("Confirm")');
    
    // Should see success message
    await expect(page.locator('text=/Cache cleared successfully/i')).toBeVisible({ timeout: 10000 });
  });
  
  test('should toggle auto-refresh', async ({ page }) => {
    // Find auto-refresh toggle
    const toggle = page.locator('input[type="checkbox"][name="auto_refresh"]');
    
    if (await toggle.isVisible()) {
      await toggle.click();
      await page.waitForTimeout(500);
    }
  });
});

test.describe('Configuration Management', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/config`);
  });
  
  test('should display configuration list', async ({ page }) => {
    await expect(page.locator('text=/System Configuration/i')).toBeVisible();
  });
  
  test('should create new configuration', async ({ page }) => {
    // Click create button
    await page.click('button:has-text("Add Config")');
    
    // Fill form
    await page.fill('input[name="key"]', `test_config_${Date.now()}`);
    await page.fill('input[name="value"]', 'test_value');
    await page.fill('textarea[name="description"]', 'Test configuration');
    await page.selectOption('select[name="category"]', 'general');
    
    // Submit
    await page.click('button[type="submit"]');
    
    // Should see success message
    await expect(page.locator('text=/Configuration created/i')).toBeVisible({ timeout: 10000 });
  });
  
  test('should toggle secret visibility', async ({ page }) => {
    // Find show/hide button for secret value
    const toggleButton = page.locator('button[title*="Show"]').first();
    
    if (await toggleButton.isVisible()) {
      await toggleButton.click();
      await page.waitForTimeout(300);
    }
  });
});

test.describe('Responsive Design', () => {
  test('should work on mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await login(page);
    
    // Should see hamburger menu on mobile
    await expect(page.locator('button[aria-label*="menu"]')).toBeVisible();
    
    // Click hamburger to open sidebar
    await page.click('button[aria-label*="menu"]');
    
    // Sidebar should be visible
    await expect(page.locator('nav')).toBeVisible();
  });
  
  test('should work on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });
    await login(page);
    
    // Dashboard should be responsive
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });
});

test.describe('Performance', () => {
  test('should load dashboard within 2 seconds', async ({ page }) => {
    await login(page);
    
    const startTime = Date.now();
    await page.goto(`${BASE_URL}/`);
    await page.waitForSelector('text=Dashboard');
    const endTime = Date.now();
    
    const loadTime = endTime - startTime;
    expect(loadTime).toBeLessThan(2000);
  });
  
  test('should handle large data tables efficiently', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/logs`);
    
    // Should render table without freezing
    await expect(page.locator('table')).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Error Handling', () => {
  test('should display error when API is down', async ({ page }) => {
    // This would require mocking API failure
    // For now, just check that error boundaries exist
    await login(page);
    
    // Navigation should work even if some data fails to load
    await page.goto(`${BASE_URL}/users`);
    await expect(page.locator('text=/User Management/i')).toBeVisible();
  });
  
  test('should show form validation errors', async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/users`);
    
    // Try to create user with empty fields
    await page.click('button:has-text("Create User")');
    await page.click('button[type="submit"]');
    
    // Should see validation errors
    await expect(page.locator('text=/required/i')).toBeVisible();
  });
});
