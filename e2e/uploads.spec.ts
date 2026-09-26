import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';

async function library(page: Page) {
  await page.route('**/api/auth/me', route => route.fulfill({ json: { name: 'Test', csrf: 'test-only' } }));
  await page.route('**/api/stats', route => route.fulfill({ json: { photos: 0, favorites: 0, albums: 1, trash: 0, original_bytes: 0, disk_total: 1000, disk_free: 900, max_upload: 41943040 } }));
  await page.route('**/api/photos?**', route => route.fulfill({ json: { items: [], total: 0 } }));
  await page.route('**/api/albums', route => route.fulfill({ json: [{ id: 'trip', name: 'Portugal', count: 0, cover: null, created_at: '2026-01-01' }] }));
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Tu vida, en imágenes.' })).toBeVisible();
}

function files(count: number) {
  const buffer = readFileSync('test-results/fixtures/recuerdo-01.jpg');
  return Array.from({ length: count }, (_, i) => ({ name: `batch-${i}.jpeg`, mimeType: 'image/jpeg', buffer }));
}

test('1000 uploads keep two requests in flight and complete without browser errors', async ({ page }) => {
  test.setTimeout(120_000);
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await library(page);
  let active = 0, maximum = 0, completed = 0;
  const names = new Set<string>();
  await page.route('**/api/photos/upload?**', async route => {
    active += 1; maximum = Math.max(maximum, active);
    names.add(new URL(route.request().url()).searchParams.get('filename')!);
    await new Promise(resolve => setTimeout(resolve, 2));
    active -= 1; completed += 1;
    await route.fulfill({ status: 201, json: { duplicate: false, photo: { id: `photo-${completed}`, deleted_at: null } } });
  });
  await page.getByLabel('Seleccionar fotos para subir').setInputFiles(files(1000));
  await expect(page.getByText('1000 guardadas · 0 ya estaban en casa', { exact: true })).toBeVisible({ timeout: 100_000 });
  expect(completed).toBe(1000); expect(names.size).toBe(1000);
  expect(maximum).toBeLessThanOrEqual(2);
  expect(errors).toEqual([]);
});

test('1000 rejected files have a bounded error list and can all be retried', async ({ page }) => {
  test.setTimeout(120_000);
  await library(page);
  let reject = true, succeeded = 0;
  await page.route('**/api/photos/upload?**', route => {
    if (reject) return route.fulfill({ status: 415, json: { detail: 'Archivo no compatible de prueba.' } });
    succeeded += 1;
    return route.fulfill({ status: 201, json: { duplicate: false, photo: { id: 'test', deleted_at: null } } });
  });
  await page.getByLabel('Seleccionar fotos para subir').setInputFiles(files(1000));
  await expect(page.getByText('Subida con pendientes', { exact: true })).toBeVisible({ timeout: 50_000 });
  await expect(page.locator('.upload-content li')).toHaveCount(20);
  await expect(page.getByText('0 guardadas · 0 ya estaban en casa · 1000 pendientes', { exact: true })).toBeVisible();
  reject = false;
  await page.getByRole('button', { name: 'Reintentar pendientes' }).click();
  await expect(page.getByText('1000 guardadas · 0 ya estaban en casa', { exact: true })).toBeVisible({ timeout: 50_000 });
  expect(succeeded).toBe(1000);
});

test('a disconnected album upload retains unstarted files and its original album for retry', async ({ page }) => {
  await library(page);
  await page.getByRole('navigation').getByRole('button', { name: /Álbumes/ }).click();
  await page.getByRole('button', { name: 'Portugal 0 fotos' }).click();
  let disconnected = true, requests = 0, linked = 0;
  await page.route('**/api/photos/upload?**', route => {
    requests += 1;
    if (disconnected) return route.abort();
    return route.fulfill({ status: 201, json: { duplicate: true, photo: { id: 'previously-saved', deleted_at: null } } });
  });
  await page.route('**/api/albums/trip/photos/*', route => {
    expect(route.request().method()).toBe('PUT'); linked += 1;
    return route.fulfill({ json: { ok: true } });
  });
  await page.getByLabel('Seleccionar fotos para subir').setInputFiles(files(1000));
  await expect(page.getByText('Subida detenida', { exact: true })).toBeVisible();
  expect(requests).toBeLessThanOrEqual(2);
  await expect(page.getByText('0 guardadas · 0 ya estaban en casa · 1000 pendientes', { exact: true })).toBeVisible();
  await page.getByRole('navigation').getByRole('button', { name: /Todas las fotos/ }).click();
  disconnected = false;
  await page.getByRole('button', { name: 'Reintentar pendientes' }).click();
  await expect(page.getByText('0 guardadas · 1000 ya estaban en casa', { exact: true })).toBeVisible({ timeout: 50_000 });
  expect(linked).toBe(1000);
});

test('cancel keeps all interrupted and unstarted files pending', async ({ page }) => {
  await library(page);
  await page.route('**/api/photos/upload?**', () => {});
  await page.getByLabel('Seleccionar fotos para subir').setInputFiles(files(1000));
  await page.getByLabel('Cancelar subidas').click();
  await expect(page.getByText('Subida detenida', { exact: true })).toBeVisible();
  await expect(page.getByText('0 guardadas · 0 ya estaban en casa · 1000 pendientes', { exact: true })).toBeVisible();
});
