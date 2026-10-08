chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "download-center-link", title: "دانلود با مرکز دانلود",
    contexts: ["link", "video", "audio"]
  });
});
chrome.contextMenus.onClicked.addListener(async (info) => {
  const url = info.srcUrl || info.linkUrl || "";
  if (/^https?:\/\//i.test(url)) {
    await chrome.storage.local.set({pendingUrl: url});
    try { await chrome.action.openPopup(); } catch (_) { /* use icon to open */ }
  }
});
