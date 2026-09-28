import { expect, test } from '@playwright/test';

test('selected photos use one request for bulk updates and album additions', async ({ page }) => {
  const photos = ['first', 'second'].map(id => ({
    id, filename: `${id}.jpg`, bytes: 1000, width: 800, height: 600,
    taken_at: '2026-05-09T12:00:00', uploaded_at: '2026-05-10T10:00:00',
    favorite: false, deleted_at: null, latitude: null, longitude: null, location_name: null,
  }));
  const photoBatches: string[][] = [];
  const albumBatches: string[][] = [];
  await page.route('**/api/auth/me', route => route.fulfill({ json: { name: 'Test', csrf: 'test-only' } }));
  await page.route('**/api/stats', route => route.fulfill({ json: {
    photos: 2, favorites: 0, albums: 1, trash: 0, original_bytes: 2000,
    disk_total: 10000, disk_free: 8000, max_upload: 41943040,
  } }));
  await page.route('**/api/albums', route => route.fulfill({ json: [{
    id: 'trip', name: 'Portugal', created_at: '2026-05-10', count: 0, cover: null,
    cover_photo_id: null, cover_x: 50, cover_y: 50,
  }] }));
  await page.route('**/api/photos?**', route => route.fulfill({ json: {
    items: photos, total: 2, next_cursor: null,
  } }));
  await page.route('**/api/photos/batch', route => {
    photoBatches.push(route.request().postDataJSON().ids);
    return route.fulfill({ json: { updated: 2 } });
  });
  await page.route('**/api/albums/trip/photos', route => {
    albumBatches.push(route.request().postDataJSON().ids);
    return route.fulfill({ json: { ok: true } });
  });

  await page.goto('/');
  for (const photo of photos) await page.getByRole('button', { name: `Seleccionar ${photo.filename}` }).click();
  await page.getByRole('button', { name: 'Marcar selección como favorita' }).click();
  await expect.poll(() => photoBatches).toEqual([['first', 'second']]);
  await expect(page.getByText('2 seleccionadas')).toHaveCount(0);

  for (const photo of photos) await page.getByRole('button', { name: `Seleccionar ${photo.filename}` }).click();
  await page.getByRole('button', { name: 'Añadir a álbum' }).click();
  await page.locator('.album-choice').click();
  await expect.poll(() => albumBatches).toEqual([['first', 'second']]);
});
