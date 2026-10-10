import { test, expect } from '@playwright/test';

test('planner completes the synthetic city workflow in the browser', async ({page}) => {
  test.setTimeout(180_000);
  page.on('dialog',d=>d.accept());
  await page.goto('http://127.0.0.1:4200/');
  await expect(page.getByRole('heading',{name:'Sign in to your workspace'})).toBeVisible();
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Password').fill(process.env['E2E_ADMIN_PASSWORD']!);
  await page.getByRole('button',{name:'Sign in'}).click();
  await expect(page.getByRole('heading',{name:'Dashboard'})).toBeVisible();
  await page.getByRole('button',{name:'Load synthetic demo'}).click();
  await expect(page.getByText('SYNTHETIC DEMO DATA')).toBeVisible();
  async function complete(label: string) {
    await page.getByRole('button',{name:label}).click();
    await expect(page.getByText('Latest job: COMPLETED')).toBeVisible({timeout:120_000});
    await expect(page.locator('[role="alert"]')).toHaveCount(0);
  }
  await page.getByRole('button',{name:'Accessibility',exact:true}).click();
  await complete('Run accessibility');
  await expect(page.getByText('Before / after comparison')).toHaveCount(0);
  await page.getByRole('button',{name:'Demand Prediction',exact:true}).click();
  await complete('Train demand models');
  await expect(page.getByText('Model comparison')).toBeVisible();
  await complete('Predict demand');
  await page.getByRole('button',{name:'Candidate Sites',exact:true}).click();
  await complete('Generate candidate sites');
  await page.getByRole('button',{name:'Optimization',exact:true}).click();
  await complete('Run optimization');
  await expect(page.getByText('Before / after comparison')).toBeVisible();
  await page.getByRole('button',{name:'Recommendations',exact:true}).click();
  await expect(page.getByText('Why this site:').first()).toBeVisible();
  await page.getByRole('button',{name:'Reports',exact:true}).click();
  await page.getByLabel('Analysis run').selectOption({index:1});
  const event=page.waitForEvent('download');
  await page.getByRole('button',{name:'Download PDF'}).click();
  expect((await event).suggestedFilename()).toMatch(/\.pdf$/);
});
