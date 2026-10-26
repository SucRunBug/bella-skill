// Call after constructing or replacing image/font assets, including from seek(t).
export async function waitForAssets() {
  await document.fonts.ready;
  await Promise.all([...document.images].map(async image => {
    if (!image.complete) await new Promise((resolve, reject) => {
      image.addEventListener('load', resolve, {once: true});
      image.addEventListener('error', () => reject(new Error(`Image failed: ${image.src}`)), {once: true});
    });
    if (!image.naturalWidth) throw new Error(`Image has no pixels: ${image.src}`);
    await image.decode();
  }));
}
