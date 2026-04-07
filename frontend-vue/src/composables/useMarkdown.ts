import { marked } from 'marked'

export function useMarkdown() {
  function simpleMarkdown(text: string): string {
    // 如果内容已经是 HTML（包含常见的 HTML 标签），直接返回
    if (/<div|<span|class=|<button|<input|<form|onclick|<section|<article/i.test(text)) {
      return text
    }

    return text
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/`(.+?)`/g, '<code>$1</code>')
      .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
      .replace(/^---$/gm, '<hr>')
      .replace(/^- (.+)$/gm, '<li>$1</li>')
      .replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>')
      .replace(/\n\n/g, '</p><p>')
      .replace(/^(?!<[hublp])/gm, '')
      .trim()
  }

  async function parseMarkdown(text: string): Promise<string> {
    return await marked(text)
  }

  function escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
  }

  return {
    simpleMarkdown,
    parseMarkdown,
    escapeHtml
  }
}
