import {
  Component,
  DestroyRef,
  ElementRef,
  afterRenderEffect,
  computed,
  inject,
  input,
  linkedSignal,
  signal,
  viewChild,
} from '@angular/core';
import type { Chart } from 'chart.js';
import { ChartSpec, ChartType } from './chat.models';

/** Colorblind-friendly categorical palette; the first color matches the widget's teal accent. */
const COLORS = ['#0f8b8d', '#2f5d9e', '#d9822b', '#7b5ea7', '#4c9a2a', '#c2413b', '#b8860b', '#6b7785'];

/**
 * An interactive chart for one answer: hover for values, click legend entries to hide a series,
 * switch between chart types, see the numbers as a table, or download a PNG.
 */
@Component({
  selector: 'app-chart-view',
  templateUrl: './chart-view.html',
  styleUrl: './chart-view.css',
})
export class ChartView {
  readonly spec = input.required<ChartSpec>();
  /** Index of the message this chart belongs to (used to find it when exporting). */
  readonly key = input.required<number>();

  protected readonly type = linkedSignal<ChartType>(() => this.spec().type);
  protected readonly showTable = signal(false);
  /** Types that make sense for this data: trends and comparisons swap between line and bar. */
  protected readonly types = computed<ChartType[]>(() =>
    this.spec().type === 'doughnut' ? ['doughnut', 'bar'] : ['line', 'bar'],
  );
  protected readonly hasLegend = computed(() => this.type() === 'doughnut' || this.spec().series.length > 1);
  protected readonly unitSuffix = computed(() => (this.spec().unit ? ` (${this.spec().unit})` : ''));

  private readonly canvas = viewChild<ElementRef<HTMLCanvasElement>>('canvas');
  private chart?: Chart;
  private resolveReady!: () => void;
  private readonly ready = new Promise<void>((resolve) => (this.resolveReady = resolve));

  constructor() {
    inject(DestroyRef).onDestroy(() => this.chart?.destroy());
    afterRenderEffect(() => {
      const canvas = this.canvas()?.nativeElement;
      if (canvas) void this.render(canvas, this.spec(), this.type());
    });
  }

  /** The chart as a PNG data URL on a white background (for PDF export and downloads). */
  async toPng(): Promise<string | null> {
    await this.ready;
    const source = this.chart?.canvas;
    if (!source) return null;
    const out = document.createElement('canvas');
    out.width = source.width;
    out.height = source.height;
    const ctx = out.getContext('2d')!;
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(0, 0, out.width, out.height);
    ctx.drawImage(source, 0, 0);
    return out.toDataURL('image/png');
  }

  protected async download(): Promise<void> {
    const png = await this.toPng();
    if (!png) return;
    const a = document.createElement('a');
    a.href = png;
    a.download = `${this.spec().title.toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 60) || 'chart'}.png`;
    a.click();
  }

  protected format(value: number | null): string {
    if (value === null) return '–';
    return value.toLocaleString(undefined, { maximumFractionDigits: 1 }) + (this.spec().unit === '%' ? '%' : '');
  }

  private async render(canvas: HTMLCanvasElement, spec: ChartSpec, type: ChartType): Promise<void> {
    // Loaded on first use so Chart.js isn't part of the page's initial bundle.
    const { Chart, registerables } = await import('chart.js');
    Chart.register(...registerables);
    this.chart?.destroy();

    const doughnut = type === 'doughnut';
    const unit = spec.unit === '%' ? '%' : spec.unit ? ` ${spec.unit}` : '';
    const fmt = (v: number) => v.toLocaleString(undefined, { maximumFractionDigits: 1 }) + unit;
    this.chart = new Chart(canvas, {
      type,
      data: {
        labels: spec.labels,
        datasets: spec.series.map((s, i) => ({
          label: s.name,
          data: s.values,
          borderColor: doughnut ? '#fff' : COLORS[i % COLORS.length],
          backgroundColor: doughnut ? spec.labels.map((_, j) => COLORS[j % COLORS.length]) : COLORS[i % COLORS.length],
          borderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6,
          tension: 0.2,
          spanGaps: true,
        })),
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 400 },
        interaction: { mode: doughnut ? 'nearest' : 'index', intersect: false },
        plugins: {
          legend: { display: doughnut || spec.series.length > 1, position: 'bottom', labels: { boxWidth: 12 } },
          tooltip: {
            callbacks: {
              // Doughnut slices parse to a number, line/bar points to {x, y}.
              label: (item) =>
                doughnut
                  ? ` ${item.label}: ${fmt(item.parsed as unknown as number)}`
                  : ` ${item.dataset.label}: ${fmt((item.parsed as { y: number }).y)}`,
            },
          },
        },
        scales: doughnut
          ? {}
          : {
              x: { grid: { display: false } },
              y: { beginAtZero: type === 'bar', ticks: { callback: (v) => fmt(Number(v)) } },
            },
      },
    });
    this.resolveReady();
  }
}
