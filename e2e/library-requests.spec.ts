import { expect, test } from '@playwright/test';

test('search and metadata-only sections avoid redundant library requests', async ({ page }) => {
  let albumRequests = 0;
  let statsRequests = 0;
  const photoQueries: string[] = [];

  await page.route('**/api/auth/me', route => route.fulfill({
    json: { name: 'Test', csrf: 'test-only' },
  }));
  await page.route('**/api/albums', route => {
    albumRequests += 1;
    return route.fulfill({ json: [] });
  });
  await page.route('**/api/stats', route => {
    statsRequests += 1;
    return route.fulfill({
      json: {
        photos: 0, favorites: 0, albums: 0, trash: 0, original_bytes: 0,
        disk_total: 1000, disk_free: 900, max_upload: 41943040,
      },
    });
  });
  await page.route('**/api/photos?**', route => {
    photoQueries.push(new URL(route.request().url()).searchParams.get('q') ?? '');
    return route.fulfill({ json: { items: [], total: 0, next_cursor: null } });
  });
  await page.route('**/api/imports', route => route.fulfill({
    json: { enabled: false, jobs: [] },
  }));

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Tu vida, en imágenes.' })).toBeVisible();
  await expect.poll(() => photoQueries).toEqual(['']);
  expect(albumRequests).toBe(1);
  expect(statsRequests).toBe(1);

  await page.getByLabel('Buscar fotos').fill('Portugal');
  await expect.poll(() => photoQueries).toEqual(['', 'Portugal']);
  expect(albumRequests).toBe(1);
  expect(statsRequests).toBe(1);

  await page.getByRole('navigation').getByRole('button', { name: /Álbumes/ }).click();
  await expect(page.getByRole('heading', { name: 'Historias que van juntas.' })).toBeVisible();
  await page.waitForTimeout(100);
  expect(photoQueries).toEqual(['', 'Portugal']);

  await page.getByRole('navigation').getByRole('button', { name: 'Mi hogar', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Aquí viven tus recuerdos.' })).toBeVisible();
  await page.waitForTimeout(100);
  expect(photoQueries).toEqual(['', 'Portugal']);
  expect(albumRequests).toBe(1);
  expect(statsRequests).toBe(1);
});
