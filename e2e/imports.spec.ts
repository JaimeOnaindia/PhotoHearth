import { test, expect } from '@playwright/test';

test('server folder import remains visible and finishes in the background', async ({ page }) => {
  const jobs: Record<string, unknown>[] = [];
  let polls = 0;
  await page.route('**/api/auth/me', route => route.fulfill({
    json: { name: 'Test', csrf: 'test-only' },
  }));
  await page.route('**/api/stats', route => route.fulfill({
    json: { photos: 0, favorites: 0, albums: 0, trash: 0, original_bytes: 0, disk_total: 1000, disk_free: 900, max_upload: 41943040 },
  }));
  await page.route('**/api/photos?**', route => route.fulfill({ json: { items: [], total: 0 } }));
  await page.route('**/api/albums', route => route.fulfill({ json: [] }));
  await page.route('**/api/imports', async route => {
    if (route.request().method() === 'POST') {
      expect(route.request().headers()['x-csrf-token']).toBe('test-only');
      expect(route.request().postDataJSON()).toEqual({ source: 'Viajes/Portugal' });
      const job = {
        id: 'import-1', source: 'Viajes/Portugal', status: 'queued',
        created_at: '2026-09-27T10:00:00Z', updated_at: '2026-09-27T10:00:00Z',
        total: 1200, finished: 0, pending: 1200, running: 0,
        imported: 0, duplicates: 0, failed: 0, canceled: 0,
      };
      jobs.unshift(job);
      return route.fulfill({ status: 202, json: job });
    }
    polls += 1;
    if (jobs.length && polls > 1) Object.assign(jobs[0], {
      status: 'completed', finished: 1200, pending: 0, imported: 1175, duplicates: 25,
    });
    return route.fulfill({ json: { enabled: true, jobs } });
  });

  await page.goto('/');
  await page.getByRole('navigation').getByRole('button', { name: 'Mi hogar', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Traer una carpeta a PhotoHearth' })).toBeVisible();
  await page.getByLabel('Subcarpeta del servidor').fill('Viajes/Portugal');
  await page.getByRole('button', { name: 'Importar carpeta' }).click();
  await expect(page.getByText('Terminada', { exact: true })).toBeVisible({ timeout: 5000 });
  await expect(page.getByText(/1175 nuevas · 25 duplicadas/)).toBeVisible();
  await expect(page.getByLabel('Progreso de Viajes/Portugal')).toHaveAttribute('value', '1200');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
});
