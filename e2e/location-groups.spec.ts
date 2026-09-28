import { expect, test } from '@playwright/test';

test('suggests missing photos from the same album and day without assigning a location', async ({ page }) => {
  const photos = ['first', 'second'].map((id, index) => ({
    id, filename: `${id}.jpg`, bytes: 1000, width: 800, height: 600,
    taken_at: `2026-05-09T12:0${index}:00`, uploaded_at: '2026-05-10T10:00:00',
    favorite: false, deleted_at: null, latitude: null, longitude: null, location_name: null,
    albums: [{ id: 'portugal', name: 'Portugal' }],
  }));
  let assignments = 0;
  await page.route('**/api/auth/me', route => route.fulfill({ json: { name: 'Test', csrf: 'test-only' } }));
  await page.route('**/api/stats', route => route.fulfill({ json: {
    photos: 2, favorites: 0, albums: 1, trash: 0, original_bytes: 2000,
    disk_total: 10000, disk_free: 8000, max_upload: 41943040,
  } }));
  await page.route('**/api/albums', route => route.fulfill({ json: [] }));
  await page.route('**/api/places', route => route.fulfill({ json: {
    items: [], total: 0, located: 0, missing: 2,
  } }));
  await page.route('**/api/photos?**', route => route.fulfill({ json: {
    items: new URL(route.request().url()).searchParams.get('location') === 'missing' ? photos : [],
    total: 2, next_cursor: null,
  } }));
  await page.route('**/api/photos/batch', route => {
    assignments += 1;
    return route.fulfill({ json: { updated: 2 } });
  });

  await page.goto('/');
  await page.getByRole('navigation').getByRole('button', { name: 'Lugares', exact: true }).click();
  await page.getByRole('button', { name: 'Organizar fotos sin ubicación' }).click();
  await page.getByRole('button', { name: /Seleccionar 2 de Portugal/ }).click();
  await expect(page.locator('.missing-photo[aria-pressed="true"]')).toHaveCount(2);
  await expect(page.getByRole('button', { name: /Situar 2 fotos/ })).toBeDisabled();
  expect(assignments).toBe(0);
});
