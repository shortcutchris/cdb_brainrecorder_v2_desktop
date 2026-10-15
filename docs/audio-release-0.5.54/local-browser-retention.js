async page => {
  const wake = {instance:'synthetic-perf',enabled:true,available:true,word:'Okay KAI',phrase:'okay-kai',state:'listening',message:'Bereit für „Okay KAI“',detections:0,recognized_for:0,testing:false};
  const requests = {state:0,wake:0};
  await page.unrouteAll({behavior:'wait'});
  await page.route('**/api/state', async route => {
    const response = await route.fetch(); const value = await response.json();
    value.wake = wake; requests.state++;
    await route.fulfill({response,json:value});
  });
  await page.route('**/api/wake/status', async route => {
    requests.wake++; await route.fulfill({json:wake});
  });
  await page.reload();
  await page.waitForFunction(() => document.querySelector('#wake-rail-led')?.dataset.state === 'listening');
  await page.waitForTimeout(5000);
  const cdp = await page.context().newCDPSession(page);
  await cdp.send('Performance.enable');
  const sample = async () => ({at:Date.now(),heap:await cdp.send('Runtime.getHeapUsage'),dom:await cdp.send('Memory.getDOMCounters'),performance:Object.fromEntries((await cdp.send('Performance.getMetrics')).metrics.map(m=>[m.name,m.value]))});
  try {
    await cdp.send('HeapProfiler.collectGarbage');
    const before = await sample();
    const intervals = [];
    for (let i=0;i<3;i++) {
      await page.waitForTimeout(20000);
      const natural = await sample();
      await cdp.send('HeapProfiler.collectGarbage');
      intervals.push({natural,after:await sample()});
    }
    return {case:'original-frontend-synthetic-wake-repeated-gc',localPreviewOnly:true,viewport:page.viewportSize(),requests,before,intervals};
  } finally { await cdp.detach(); }
}
