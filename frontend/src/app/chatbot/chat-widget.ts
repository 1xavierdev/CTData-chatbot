import {
  Component,
  ElementRef,
  afterRenderEffect,
  computed,
  inject,
  signal,
  viewChild,
  viewChildren,
} from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  ChatMessage,
  ChatProfile,
  ExportFormat,
  ONBOARDING_STEPS,
} from './chat.models';
import { ChatService } from './chat.service';
import { ChartView } from './chart-view';
import { FormatMessagePipe } from './format-message.pipe';

@Component({
  selector: 'app-chat-widget',
  imports: [FormsModule, FormatMessagePipe, TitleCasePipe, ChartView],
  templateUrl: './chat-widget.html',
  styleUrl: './chat-widget.css',
  host: { '(document:keydown.escape)': 'close()' },
})
export class ChatWidget {
  private readonly chat = inject(ChatService);

  protected readonly steps = ONBOARDING_STEPS;

  protected readonly isOpen = signal(false);
  protected readonly messages = signal<ChatMessage[]>([]);
  protected readonly loading = signal(false);
  /** "<message index>:<format>" while that file is being built. */
  protected readonly exporting = signal<string | null>(null);
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
    if (s < 0) return 'Ask about Connecticut data…';
    return this.steps[s].freeText ? 'Pick an option or type your answer…' : 'Pick an option above…';
  });
  protected readonly profileSummary = computed(() => {
    const p = this.profile();
    return p ? this.steps.map((s) => ({ label: s.key, value: p[s.key] })).filter((x) => x.value) : [];
  });

  private readonly scroller = viewChild<ElementRef<HTMLElement>>('scroller');
  private readonly inputEl = viewChild<ElementRef<HTMLTextAreaElement>>('input');
  private readonly charts = viewChildren(ChartView);

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
        content: `Welcome back! I'll keep tailoring answers for you${p.profession ? ` as a **${p.profession}**` : ''}. What would you like to know about Connecticut data?`,
      });
      this.chatStart = this.messages().length;
      return;
    }
    this.push({
      role: 'assistant',
      content:
        "Hi! I'm the **CTData Assistant**. I can help you find and understand **Connecticut data**: education, health, housing, the economy, population and more.\n\nSo I can explain things in a way that's most useful for you, I'll ask 4 quick questions.",
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
        ? `Thanks! I'll tailor my answers for you (${who}). What would you like to know?`
        : 'No problem! What would you like to know?',
    });
    this.chatStart = this.messages().length;
  }

  private send(text: string): void {
    const history = this.messages().slice(this.chatStart);
    this.push({ role: 'user', content: text });
    this.loading.set(true);
    this.chat.ask(text, this.profile() ?? {}, history).subscribe({
      next: (res) => {
        if (res.export_previous) {
          // "make a ppt of this": export the latest real answer.
          const list = this.messages();
          let target = list.length - 1;
          while (target >= 0 && !this.canExport(list[target])) target--;
          this.push({
            role: 'assistant',
            content: target < 0 ? 'Ask me a question first, then I can turn the answer into a PDF or PowerPoint.' : res.answer,
            mode: res.mode,
          });
          this.loading.set(false);
          if (target >= 0 && res.export) void this.exportMessage(target, res.export);
          return;
        }
        this.push({
          role: 'assistant',
          content: res.answer,
          sources: res.sources,
          mode: res.mode,
          chart: res.chart,
          question: text,
        });
        this.loading.set(false);
        if (res.export) void this.exportMessage(this.messages().length - 1, res.export);
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

  protected canExport(m: ChatMessage): boolean {
    return m.role === 'assistant' && (m.mode === 'llm' || m.mode === 'offline');
  }

  /** Download one answer (with its chart, if any) as a PDF or PowerPoint file. */
  protected async exportMessage(index: number, format: ExportFormat): Promise<void> {
    const m = this.messages()[index];
    if (!m || this.exporting()) return;
    this.exporting.set(`${index}:${format}`);
    try {
      // Wait a tick so a chart that was just added has rendered, then capture it for the PDF.
      await new Promise((resolve) => setTimeout(resolve));
      const view = this.charts().find((c) => c.key() === index);
      const chartPng = m.chart && format === 'pdf' ? await view?.toPng() : null;
      await this.chat.download({
        format,
        title: m.question ?? 'CTData Assistant answer',
        answer: m.content,
        sources: m.sources ?? [],
        chart: m.chart,
        chart_png: chartPng,
      });
    } catch {
      this.push({ role: 'assistant', content: "Sorry, I couldn't create that file. Please try again." });
    } finally {
      this.exporting.set(null);
    }
  }

  private push(message: ChatMessage): void {
    this.messages.update((list) => [...list, message]);
  }
}
