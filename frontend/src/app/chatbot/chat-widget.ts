import {
  Component,
  ElementRef,
  afterRenderEffect,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  ChatMessage,
  ChatProfile,
  ONBOARDING_STEPS,
  SUGGESTED_QUESTIONS,
} from './chat.models';
import { ChatService } from './chat.service';
import { FormatMessagePipe } from './format-message.pipe';

@Component({
  selector: 'app-chat-widget',
  imports: [FormsModule, FormatMessagePipe, TitleCasePipe],
  templateUrl: './chat-widget.html',
  styleUrl: './chat-widget.css',
  host: { '(document:keydown.escape)': 'close()' },
})
export class ChatWidget {
  private readonly chat = inject(ChatService);

  protected readonly steps = ONBOARDING_STEPS;
  protected readonly suggestions = SUGGESTED_QUESTIONS;

  protected readonly isOpen = signal(false);
  protected readonly messages = signal<ChatMessage[]>([]);
  protected readonly loading = signal(false);
  protected readonly profile = signal<ChatProfile | null>(this.chat.loadProfile());
  /** Index into ONBOARDING_STEPS while onboarding; -1 once the profile is complete. */
  protected readonly step = signal(this.profile() ? -1 : 0);
  protected draft = '';

  private answers: ChatProfile = {};
  /** Messages before this index are onboarding and aren't sent to the model as history. */
  private chatStart = 0;

  protected readonly onboarding = computed(() => this.step() >= 0);
  protected readonly placeholder = computed(() => {
    const s = this.step();
    if (s < 0) return 'Ask about Connecticut education data…';
    return this.steps[s].freeText ? 'Pick an option or type your answer…' : 'Pick an option above…';
  });
  protected readonly profileSummary = computed(() => {
    const p = this.profile();
    return p ? this.steps.map((s) => ({ label: s.key, value: p[s.key] })).filter((x) => x.value) : [];
  });

  private readonly scroller = viewChild<ElementRef<HTMLElement>>('scroller');
  private readonly inputEl = viewChild<ElementRef<HTMLTextAreaElement>>('input');

  constructor() {
    afterRenderEffect(() => {
      this.messages();
      this.loading();
      const el = this.scroller()?.nativeElement;
      if (el) el.scrollTop = el.scrollHeight;
    });
  }

  open(): void {
    this.isOpen.set(true);
    if (this.messages().length === 0) this.greet();
    setTimeout(() => this.inputEl()?.nativeElement.focus(), 250);
  }

  close(): void {
    this.isOpen.set(false);
  }

  /** Forget the profile and run the onboarding questions again. */
  restart(): void {
    this.chat.saveProfile(null);
    this.profile.set(null);
    this.answers = {};
    this.messages.set([]);
    this.step.set(0);
    this.greet();
  }

  protected isLast(i: number): boolean {
    return i === this.messages().length - 1;
  }

  protected choose(option: string): void {
    if (this.loading()) return;
    if (this.onboarding()) this.answerStep(option);
    else this.send(option);
  }

  protected submit(): void {
    const text = this.draft.trim();
    if (!text || this.loading()) return;
    this.draft = '';
    if (this.onboarding()) this.answerStep(text);
    else this.send(text);
  }

  protected onKeydown(event: KeyboardEvent): void {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.submit();
    }
  }

  protected skipOnboarding(): void {
    this.push({ role: 'user', content: 'Skip these questions' });
    this.finishOnboarding();
  }

  private greet(): void {
    const p = this.profile();
    if (p) {
      this.push({
        role: 'assistant',
        content: `Welcome back! I'll keep tailoring answers for you${p.profession ? ` as a **${p.profession}**` : ''}. What would you like to know about Connecticut education data?`,
        options: this.suggestions.slice(0, 3),
      });
      this.chatStart = this.messages().length;
      return;
    }
    this.push({
      role: 'assistant',
      content:
        "Hi! I'm the **CTData Assistant**. I can help you find and understand Connecticut **education data**.\n\nSo I can explain things in a way that's most useful for you, I'll ask 4 quick questions.",
    });
    this.askStep(0);
  }

  private askStep(i: number): void {
    const s = this.steps[i];
    this.push({ role: 'assistant', content: s.question, options: s.options });
  }

  private answerStep(value: string): void {
    const i = this.step();
    this.push({ role: 'user', content: value });
    this.answers = { ...this.answers, [this.steps[i].key]: value };
    if (i + 1 < this.steps.length) {
      this.step.set(i + 1);
      this.askStep(i + 1);
    } else {
      this.finishOnboarding();
    }
  }

  private finishOnboarding(): void {
    const p = this.answers;
    this.profile.set(p);
    this.chat.saveProfile(p);
    this.step.set(-1);
    const who = [p.profession, p.age && `age ${p.age}`, p.education].filter(Boolean).join(', ');
    this.push({
      role: 'assistant',
      content: who
        ? `Thanks! I'll tailor my answers for you (${who}). What would you like to know? Here are some ideas:`
        : 'No problem! What would you like to know? Here are some ideas:',
      options: this.suggestions,
    });
    this.chatStart = this.messages().length;
  }

  private send(text: string): void {
    const history = this.messages().slice(this.chatStart);
    this.push({ role: 'user', content: text });
    this.loading.set(true);
    this.chat.ask(text, this.profile() ?? {}, history).subscribe({
      next: (res) => {
        this.push({ role: 'assistant', content: res.answer, sources: res.sources, mode: res.mode });
        this.loading.set(false);
      },
      error: () => {
        this.push({
          role: 'assistant',
          content: "Sorry, I couldn't reach the CTData assistant server. Is `python server.py` running?",
        });
        this.loading.set(false);
      },
    });
  }

  private push(message: ChatMessage): void {
    this.messages.update((list) => [...list, message]);
  }
}
