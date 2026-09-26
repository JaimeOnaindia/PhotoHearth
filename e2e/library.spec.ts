import { test, expect } from '@playwright/test';

test('private photo library works from upload to restore', async ({ page }, info) => {
  const errors: string[] = [];
  const external: string[] = [];
  const tiles: string[] = [];
  // Never download public map tiles from automated browser tests.
  await page.route('https://tile.openstreetmap.org/**', route => route.fulfill({
    contentType: 'image/svg+xml', body: '<svg xmlns="http://www.w3.org/2000/svg" width="256" height="256"><rect width="256" height="256" fill="#e8eedf"/><path d="M0 120H256M120 0V256" stroke="#fcfaf2" stroke-width="12"/></svg>',
  }));
  page.on('pageerror', error => errors.push(error.message));
  page.on('request', request => {
    if (request.url().startsWith('https://tile.openstreetmap.org/')) tiles.push(request.url());
    else if (!request.url().startsWith('http://127.0.0.1:8765') && !request.url().startsWith('data:')) external.push(request.url());
  });
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Lo que importa/ })).toBeVisible();
  await page.screenshot({ path: `test-results/login-${info.project.name}.png`, fullPage: true });
  await page.getByLabel('Contraseña de tu hogar').fill('photohearth-test-only-password');
  await page.getByRole('button', { name: 'Entrar a mi biblioteca' }).click();
  await expect(page.getByRole('heading', { name: 'Tu vida, en imágenes.' })).toBeVisible();
  await expect(page.getByLabel('Cargando biblioteca')).toHaveCount(0);
  await page.screenshot({ path: `test-results/empty-${info.project.name}.png`, fullPage: true });
  await page.getByLabel('Seleccionar fotos para subir').setInputFiles(Array.from({ length: 12 }, (_, i) => `test-results/fixtures/recuerdo-${String(i + 1).padStart(2, '0')}.jpg`));
  await expect(page.getByText('Subida terminada', { exact: true })).toBeVisible({ timeout: 30_000 });
  await page.getByLabel('Cerrar subidas').click();
  await expect(page.locator('.photo-card')).toHaveCount(12);
  await expect(page.locator('.photo-card img').first()).toBeVisible();
  expect(await page.locator('.photo-card img').evaluateAll(images => images.every(image => (image as HTMLImageElement).naturalWidth > 0))).toBeTruthy();
  await page.screenshot({ path: `test-results/library-${info.project.name}.png`, fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.getByLabel('Buscar fotos').fill('recuerdo-01');
  await expect(page.locator('.photo-card')).toHaveCount(1);
  await page.getByRole('button', { name: 'Abrir recuerdo-01.jpg', exact: true }).click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.getByLabel('Añadir a favoritos', { exact: true }).click();
  await expect(page.getByLabel('Quitar de favoritos', { exact: true })).toBeVisible();
  const download = page.waitForEvent('download');
  await page.getByLabel('Descargar original').click();
  expect((await download).suggestedFilename()).toBe('recuerdo-01.jpg');
  await page.getByRole('button', { name: 'Añadir a álbum', exact: true }).click();
  await page.getByLabel('Nombre del nuevo álbum').fill(`Mi verano ${info.project.name}`);
  await page.getByRole('button', { name: 'Crear álbum', exact: true }).click();
  await expect(page.getByRole('heading', { name: `Mi verano ${info.project.name}`, exact: true })).toBeVisible();
  await expect(page.locator('.photo-card')).toHaveCount(1);
  // Uploading an existing original from an album must add it to that album,
  // even when the server deduplicates the upload.
  await page.getByLabel('Seleccionar fotos para subir').setInputFiles('test-results/fixtures/recuerdo-02.jpg');
  await expect(page.getByText('Subida terminada', { exact: true })).toBeVisible();
  await page.getByLabel('Cerrar subidas').click();
  await expect(page.locator('.photo-card')).toHaveCount(2);
  await page.getByRole('button', { name: 'Abrir recuerdo-01.jpg', exact: true }).click();
  await page.getByLabel('Mover a la papelera', { exact: true }).click();
  await expect(page.getByRole('dialog')).toHaveCount(0);
  await page.getByRole('navigation').getByRole('button', { name: /Papelera/ }).click();
  await page.getByRole('button', { name: 'Abrir recuerdo-01.jpg', exact: true }).click();
  await page.getByLabel('Restaurar foto', { exact: true }).click();
  await expect(page.locator('.photo-card')).toHaveCount(0);
  await page.getByRole('navigation').getByRole('button', { name: /Favoritos/ }).click();
  await expect(page.locator('.photo-card')).toHaveCount(1);
  // Reset favorite for the next viewport's independent workflow.
  await page.getByRole('button', { name: 'Abrir recuerdo-01.jpg', exact: true }).click();
  await page.getByLabel('Quitar de favoritos', { exact: true }).click();
  await page.getByRole('dialog').getByLabel('Cerrar', { exact: true }).click();
  await page.getByRole('navigation').getByRole('button', { name: 'Lugares', exact: true }).click();
  await expect(page.locator('.place-card')).toHaveCount(3);
  expect(tiles).toHaveLength(0);
  await page.getByRole('button', { name: 'Activar mapa', exact: true }).click();
  await expect(page.locator('.map-consent')).toHaveCount(0);
  await expect.poll(() => tiles.length).toBeGreaterThan(0);
  await expect(page.locator('.memory-marker')).toHaveCount(3);
  await page.screenshot({ path: `test-results/places-${info.project.name}.png`, fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.locator('.place-card').first().click();
  await expect(page.locator('.place-photos .photo-card')).toHaveCount(4);
  await page.locator('.place-photos .photo-card').first().click();
  await page.getByRole('button', { name: 'Editar ubicación', exact: true }).click();
  await page.getByLabel('Nombre del lugar', { exact: true }).fill('Nuestro viaje');
  await page.getByRole('button', { name: 'Guardar ubicación', exact: true }).click();
  await expect(page.getByRole('dialog').getByText('Ubicación actualizada.', { exact: true })).toBeVisible();
  await page.getByRole('dialog').getByLabel('Cerrar', { exact: true }).click();
  await page.getByRole('navigation').getByRole('button', { name: 'Mi hogar', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'El espacio de tus recuerdos' })).toBeVisible();
  await expect(page.getByLabel('Espacio ocupado del disco')).toBeVisible();
  expect(external).toEqual([]);
  expect(errors).toEqual([]);
  // Reuse only the fixture password so the next viewport starts independently.
  // Distinct new passwords and rejection of old ones are covered by API tests.
  await page.getByLabel('Contraseña actual', { exact: true }).fill('photohearth-test-only-password');
  await page.getByLabel('Nueva contraseña', { exact: true }).fill('photohearth-test-only-password');
  await page.getByLabel('Repite la nueva contraseña', { exact: true }).fill('mismatched-test-password');
  await page.getByRole('button', { name: 'Cambiar y cerrar sesiones' }).click();
  await expect(page.getByRole('alert')).toHaveText('Las contraseñas nuevas no coinciden.');
  await page.getByLabel('Repite la nueva contraseña', { exact: true }).fill('photohearth-test-only-password');
  await page.screenshot({ path: `test-results/password-${info.project.name}.png`, fullPage: true });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.getByRole('button', { name: 'Cambiar y cerrar sesiones' }).click();
  await expect(page.getByRole('button', { name: 'Entrar a mi biblioteca' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Entrar a mi biblioteca' })).toBeVisible();
  expect((await page.request.get('/api/photos')).status()).toBe(401);
});

test('shows a recoverable connection error instead of an empty library', async ({ page }) => {
  await page.route('**/api/auth/me', route => route.abort());
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Tu hogar está desconectado.' })).toBeVisible();
  await page.unroute('**/api/auth/me');
  await page.getByRole('button', { name: 'Volver a intentar' }).click();
  await expect(page.getByRole('button', { name: 'Entrar a mi biblioteca' })).toBeVisible();
});
