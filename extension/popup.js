const $ = id => document.getElementById(id);
const API = "http://127.0.0.1:18765";
const token = typeof BRIDGE_TOKEN === "string" ? BRIDGE_TOKEN : "";
const labels = {queued:"در صف",running:"در حال دانلود",done:"تکمیل",error:"خطا",cancelled:"لغو شد"};
function say(message, error=false) {
  $("message").textContent = message;
  $("message").className = error ? "error" : "success";
}
function validateUrl(value) {
  const url = new URL(value.trim());
  if (!["http:","https:"].includes(url.protocol)) throw Error("لینک معتبر وارد کنید");
  return url.href;
}
async function call(path, data) {
  if (!token) throw Error("پیکربندی سرویس پیدا نشد.");
  const options = {headers:{"X-Download-Token":token}};
  if (data) {
    options.method = "POST";
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(data);
  }
  let response;
  try {response = await fetch(API + path, options);}
  catch (_) {throw Error("سرویس محلی فعال نیست. start.sh را اجرا کنید.");}
  const result = await response.json();
  if (!response.ok) throw Error(result.error || "خطای سرویس");
  return result;
}
async function health() {
  try {
    await call("/api/health");
    $("health").textContent="متصل";$("health").className="ok";
  } catch (_) {
    $("health").textContent="آفلاین";$("health").className="bad";
  }
}
async function activeUrl() {
  const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
  if (tab && /^https?:\/\//.test(tab.url || "")) $("url").value=tab.url;
  else say("صفحه فعلی لینک قابل استفاده ندارد.",true);
}
async function inspect() {
  $("inspect").disabled=true;
  say("در حال بررسی...");
  try {
    const d=await call("/api/inspect",{url:validateUrl($("url").value)});
    $("info").hidden=false;
    $("info").textContent=(d.title || "محتوا")+" | "+(d.site || "وب")+" | "+(d.heights || []).map(h=>h+"p").join("، ");
    say("لینک بررسی شد.");
  } catch(e) {say(e.message,true);}
  finally {$("inspect").disabled=false;}
}
async function download() {
  $("download").disabled=true;
  try {
    await call("/api/download",{url:validateUrl($("url").value),quality:$("quality").value,mode:$("mode").value});
    say("دانلود به صف اضافه شد.");await refresh();
  } catch(e) {say(e.message,true);}
  finally {$("download").disabled=false;}
}
async function refresh() {
  try {
    const result=await call("/api/jobs");
    const area=$("jobs");area.replaceChildren();
    if (!result.jobs.length) {area.textContent="هنوز دانلودی شروع نشده است.";return;}
    for (const job of result.jobs) {
      const box=document.createElement("div");box.className="job";
      const top=document.createElement("div");top.className="jobTop";
      const name=document.createElement("span");name.className="jobUrl";
      name.textContent=job.url;name.title=job.url;
      const badge=document.createElement("span");badge.className="pill";
      badge.textContent=labels[job.state] || job.state;
      top.append(name,badge);box.append(top);
      const progress=document.createElement("div");progress.className="progress";
      const fill=document.createElement("span");fill.style.width=(job.progress || 0)+"%";
      progress.append(fill);box.append(progress);
      const bottom=document.createElement("div");bottom.className="jobBottom";
      const pct=document.createElement("span");pct.textContent=(job.progress || 0).toFixed(1)+"%";
      bottom.append(pct);
      if (job.state==="running" || job.state==="queued") {
        const cancel=document.createElement("button");cancel.className="danger";cancel.textContent="لغو";
        cancel.addEventListener("click",async()=>{
          try {await call("/api/cancel",{id:job.id});await refresh();}
          catch(e){say(e.message,true);}
        });bottom.append(cancel);
      } else if (job.error) {
        const error=document.createElement("span");error.className="error";
        error.textContent=job.error.slice(-80);error.title=job.error;bottom.append(error);
      }
      box.append(bottom);area.append(box);
    }
  } catch(e) {$("jobs").textContent=e.message;}
}
function mediaOnPage() {
  const urls=new Set();
  const add=url=>{
    if (url && /^https?:\/\//i.test(url) && url.length<2000) urls.add(url);
  };
  document.querySelectorAll("video,audio,source").forEach(el=>{
    add(el.currentSrc);add(el.src);
  });
  document.querySelectorAll("a[href]").forEach(el=>{
    if (/\.(mp4|webm|mov|m4v|mp3|m4a|ogg|wav)(?:[?#]|$)/i.test(el.href)) add(el.href);
  });
  return [...urls].slice(0,25);
}
async function scan() {
  const area=$("found");area.textContent="در حال اسکن...";
  try {
    const [tab]=await chrome.tabs.query({active:true,currentWindow:true});
    if (!tab || !tab.id || !/^https?:\/\//.test(tab.url || "")) throw Error("این صفحه قابل اسکن نیست.");
    const result=await chrome.scripting.executeScript({target:{tabId:tab.id},func:mediaOnPage});
    const urls=[...new Set(result.flatMap(r=>r.result || []))];
    area.replaceChildren();
    if (!urls.length) {
      area.textContent="فایل مستقیم پیدا نشد؛ از کادر لینک بالا استفاده کنید.";
      return;
    }
    for (const url of urls) {
      const item=document.createElement("div");item.className="mediaitem";
      const title=document.createElement("span");title.textContent=url;title.title=url;
      const btn=document.createElement("button");btn.textContent="دانلود مستقیم";
      btn.addEventListener("click",async()=>{
        try {
          const raw=decodeURIComponent(new URL(url).pathname.split("/").pop() || "media");
          const name=raw.replace(/[^a-zA-Z0-9_.() -]/g,"_").slice(0,120)||"media";
          await chrome.downloads.download({url,filename:"DownloadCenter/"+name,conflictAction:"uniquify"});
          say("فایل به دانلودهای Chrome اضافه شد.");
        } catch(e) {say("دانلود مستقیم ممکن نشد: "+e.message,true);}
      });
      item.append(title,btn);area.append(item);
    }
  } catch(e) {area.textContent="اسکن ناموفق: "+e.message;}
}
$("tabUrl").addEventListener("click",activeUrl);
$("inspect").addEventListener("click",inspect);
$("download").addEventListener("click",download);
$("scan").addEventListener("click",scan);
$("refresh").addEventListener("click",refresh);
$("mode").addEventListener("change",()=>{
  $("quality").disabled=$("mode").value==="mp3";
});
(async()=>{
  const data=await chrome.storage.local.get("pendingUrl");
  if (data.pendingUrl) {
    $("url").value=data.pendingUrl;
    await chrome.storage.local.remove("pendingUrl");
  } else await activeUrl();
  await health();
  await refresh();
  setInterval(()=>{health();refresh();},4000);
})();
