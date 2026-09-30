import { Component } from '@angular/core';

@Component({
  selector: 'app-site-footer',
  template: `
    <footer>
      <div class="wrap">
        <div>
          <p class="logo"><span>CT</span>Data</p>
          <p>Connecting people and data for good.</p>
          <p><a href="mailto:info@ctdata.org">info&#64;ctdata.org</a> · <a href="tel:860-500-1983">860-500-1983</a></p>
        </div>
        <div>
          <h4>Explore</h4>
          <a href="https://www.ctdata.org/data-by-topic" target="_blank" rel="noopener">Data by Topic</a>
          <a href="https://www.ctdata.org/education" target="_blank" rel="noopener">Education Data</a>
          <a href="https://www.ctdata.org/census" target="_blank" rel="noopener">Census</a>
        </div>
        <div>
          <h4>Get help</h4>
          <a href="https://www.ctdata.org/datahelpline" target="_blank" rel="noopener">Ask a Data Question</a>
          <a href="https://www.ctdata.org/consultation" target="_blank" rel="noopener">Explore a Customized Project</a>
          <a href="https://www.ctdata.org/newsletter-signups" target="_blank" rel="noopener">Sign up for Newsletter</a>
        </div>
      </div>
      <p class="demo-note">Hackathon prototype for demonstration only. Not the official CTData website. Content adapted from ctdata.org.</p>
    </footer>
  `,
  styles: `
    footer { background: var(--ct-navy); color: #c9d3df; }
    .wrap { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 40px; max-width: 1240px; margin: 0 auto; padding: 56px 24px 32px; }
    .logo { margin: 0 0 8px; font: 800 28px var(--ct-sans); color: #fff; }
    .logo span { color: var(--ct-teal-light); }
    h4 { margin: 0 0 12px; color: #fff; font-size: 14px; text-transform: uppercase; letter-spacing: 0.8px; }
    a { display: block; margin-bottom: 8px; color: #c9d3df; text-decoration: none; }
    p a { display: inline; }
    a:hover { color: #fff; }
    .demo-note { margin: 0; padding: 16px 24px; border-top: 1px solid rgb(255 255 255 / 0.12); text-align: center; font-size: 13px; color: #8fa0b4; }
    @media (max-width: 760px) { .wrap { grid-template-columns: 1fr; gap: 24px; } }
  `,
})
export class SiteFooter {}
