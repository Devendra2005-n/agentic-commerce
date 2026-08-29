const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({
    headless: "new",
    args: ['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream']
  });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
  
  await page.goto('http://localhost:5174');
  
  // Wait for login or bypass login if there's a quick way
  // Actually, we don't have a backend mock, so we need to click the "Test Voice" button.
  // But wait! We have a login screen first.
  console.log("Waiting for email input...");
  await page.waitForSelector('input[type="email"]');
  await page.type('input[type="email"]', 'test@example.com');
  await page.type('input[type="password"]', 'password123');
  
  console.log("Clicking sign in/up...");
  // Click the sign up text first to create account just in case
  await page.click('.auth-switch span'); // Switch to Sign Up
  await page.click('.auth-btn'); // Click sign up
  
  console.log("Waiting for dashboard...");
  // Wait for the mic button
  await page.waitForSelector('.mic-btn', { timeout: 10000 });
  console.log("Dashboard loaded!");
  
  // Click the test button
  console.log("Clicking Test Voice button...");
  await page.click('button[title="Test Voice"]');
  
  // Wait 2 seconds for auto-send to happen
  await new Promise(r => setTimeout(r, 2000));
  
  // Check the input value
  const inputValue = await page.$eval('.chat-input-wrapper input', el => el.value);
  console.log("Input box value is:", `"${inputValue}"`);
  
  // Check the messages
  const messages = await page.$$eval('.message-container .message', els => els.map(el => el.textContent));
  console.log("Messages in chat:");
  console.log(messages);
  
  await browser.close();
})();
