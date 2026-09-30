import { Component, signal } from '@angular/core';

interface NavItem {
  label: string;
  links: { label: string; href: string }[];
}

@Component({
  selector: 'app-site-header',
  template: `
    <header class="site-header">
      <div class="wrap">
        <a class="logo" href="/" aria-label="CTData home">
          <span class="word"><span class="mark">CT</span>Data</span>
          <small>Connecticut Data Collaborative</small>
        </a>

        <button class="menu-toggle" (click)="menuOpen.set(!menuOpen())" [attr.aria-expanded]="menuOpen()" aria-label="Menu">
          <span></span><span></span><span></span>
        </button>

        <nav [class.open]="menuOpen()" aria-label="Main">
          <ul>
            @for (item of nav; track item.label) {
              <li class="has-menu">
                <a href="#">{{ item.label }}</a>
                <ul class="dropdown">
                  @for (l of item.links; track l.label) {
                    <li><a [href]="'https://www.ctdata.org' + l.href" target="_blank" rel="noopener">{{ l.label }}</a></li>
                  }
                </ul>
              </li>
            }
          </ul>
          <a class="cta" href="#topics">Access Data</a>
        </nav>
      </div>
    </header>
  `,
  styles: `
    .site-header { position: sticky; top: 0; z-index: 50; background: #fff; border-bottom: 1px solid var(--ct-line); }
    .wrap { display: flex; align-items: center; justify-content: space-between; gap: 24px; max-width: 1240px; margin: 0 auto; padding: 14px 24px; }
    .logo { display: flex; flex-direction: column; text-decoration: none; line-height: 1; }
    .mark { color: var(--ct-teal); }
    .word { font: 800 30px var(--ct-sans); color: var(--ct-navy); }
    .logo small { margin-top: 4px; color: var(--ct-muted); font-size: 11px; letter-spacing: 0.4px; }
    nav { display: flex; align-items: center; gap: 20px; }
    nav > ul { display: flex; gap: 4px; margin: 0; padding: 0; list-style: none; }
    .has-menu { position: relative; }
    .has-menu > a { display: block; padding: 10px 12px; color: var(--ct-navy); font-weight: 600; font-size: 15px; text-decoration: none; }
    .has-menu > a:hover { color: var(--ct-teal); }
    .dropdown { position: absolute; top: 100%; left: 0; min-width: 240px; margin: 0; padding: 8px 0; list-style: none; background: #fff; border: 1px solid var(--ct-line); border-radius: 10px; box-shadow: 0 12px 30px rgb(19 41 75 / 0.12); opacity: 0; visibility: hidden; transform: translateY(6px); transition: 0.15s; }
    .has-menu:hover .dropdown, .has-menu:focus-within .dropdown { opacity: 1; visibility: visible; transform: none; }
    .dropdown a { display: block; padding: 8px 16px; color: var(--ct-ink); font-size: 14px; text-decoration: none; }
    .dropdown a:hover { background: var(--ct-bg); color: var(--ct-teal); }
    .cta { padding: 11px 20px; border-radius: 999px; background: var(--ct-gold); color: var(--ct-navy); font-weight: 700; text-decoration: none; white-space: nowrap; }
    .cta:hover { filter: brightness(1.05); }
    .menu-toggle { display: none; flex-direction: column; gap: 5px; padding: 8px; border: 0; background: none; cursor: pointer; }
    .menu-toggle span { width: 24px; height: 2px; background: var(--ct-navy); }
    @media (max-width: 1000px) {
      .menu-toggle { display: flex; }
      nav { display: none; position: absolute; top: 100%; left: 0; right: 0; flex-direction: column; align-items: stretch; padding: 12px 24px 20px; background: #fff; border-bottom: 1px solid var(--ct-line); }
      nav.open { display: flex; }
      nav > ul { flex-direction: column; }
      .dropdown { display: none; }
    }
  `,
})
export class SiteHeader {
  protected readonly menuOpen = signal(false);

  // Mirrors the ctdata.org main menu.
  protected readonly nav: NavItem[] = [
    { label: 'Data Resources', links: [
      { label: 'Data by Topic', href: '/data-by-topic' },
      { label: 'Interactive Data Projects', href: '/interactive-data-projects' },
      { label: 'Census', href: '/census' },
      { label: 'Geographic Resources', href: '/geographic-resources' },
      { label: 'Research', href: '/research' },
    ] },
    { label: 'Learn Data Skills', links: [
      { label: 'Build Your Data Literacy', href: '/data-literacy' },
      { label: 'Analyzing Quantitative Data', href: '/quantitative-data-analysis' },
      { label: 'Become a Data Storyteller', href: '/datastorytelling' },
      { label: 'Create Impactful Data Visualizations', href: '/data-visualization' },
      { label: 'Youth Data Programs', href: '/youth-data-programs' },
    ] },
    { label: 'Events', links: [
      { label: 'Event Calendar', href: '/event-calendar' },
      { label: 'Community of Practice', href: '/equityindata' },
      { label: 'Conferences', href: '/conferences' },
    ] },
    { label: 'Data Services', links: [
      { label: 'Data Strategic Planning', href: '/datastrategicplanning' },
      { label: 'Data Consulting', href: '/consulting' },
    ] },
    { label: 'Who We Are', links: [
      { label: 'About', href: '/about' },
      { label: 'Blog', href: '/blog' },
      { label: 'Hartford Data Collaborative', href: '/about-hdc' },
      { label: 'Our Team', href: '/our-team' },
      { label: 'Join Us', href: '/hiring' },
    ] },
  ];
}
