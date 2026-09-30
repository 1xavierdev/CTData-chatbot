import { Pipe, PipeTransform } from '@angular/core';

/**
 * Turns the small subset of Markdown the model produces (bold, bullet lists,
 * links, paragraphs) into HTML. Input is HTML-escaped first, and Angular's
 * [innerHTML] sanitizer runs on the result as well.
 */
@Pipe({ name: 'formatMessage' })
export class FormatMessagePipe implements PipeTransform {
  transform(text: string): string {
    const escaped = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const inline = (s: string) =>
      s
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>')
        .replace(/(^|[\s(])(https?:\/\/[^\s)<]+)/g, (_, pre, url) => {
          const label = url.replace(/^https?:\/\/(www\.)?/, '').replace(/\?.*$/, '');
          return `${pre}<a href="${url}" target="_blank" rel="noopener">${label}</a>`;
        });

    const blocks: string[] = [];
    let list: string[] = [];
    const flushList = () => {
      if (list.length) blocks.push(`<ul>${list.map((li) => `<li>${inline(li)}</li>`).join('')}</ul>`);
      list = [];
    };
    for (const line of escaped.split('\n')) {
      const bullet = line.match(/^\s*(?:[-*•]|\d+\.)\s+(.*)$/);
      if (bullet) {
        list.push(bullet[1]);
      } else {
        flushList();
        if (line.trim()) blocks.push(`<p>${inline(line.replace(/^#+\s*/, ''))}</p>`);
      }
    }
    flushList();
    return blocks.join('');
  }
}
