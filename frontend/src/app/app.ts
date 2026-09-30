import { Component } from '@angular/core';
import { ChatWidget } from './chatbot/chat-widget';
import { Home } from './home/home';
import { SiteFooter } from './layout/site-footer';
import { SiteHeader } from './layout/site-header';

@Component({
  selector: 'app-root',
  imports: [SiteHeader, Home, SiteFooter, ChatWidget],
  template: `
    <app-site-header />
    <main>
      <app-home (askAssistant)="chat.open()" />
    </main>
    <app-site-footer />
    <app-chat-widget #chat />
  `,
})
export class App {}
