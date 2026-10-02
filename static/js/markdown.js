/**
 * 轻量 Markdown 渲染器（无第三方依赖，离线可用）
 * 覆盖助手回复所需的语法：标题 / 表格 / 列表 / 引用 / 分隔线 / 代码块
 * 行内：图片 / 链接 / 粗体 / 斜体 / 行内代码
 * 安全策略：先整体转义 HTML，再按语法拼装标签，避免 XSS。
 */
(function (global) {
  "use strict";

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderInline(text) {
    return text
      // 图片 ![alt](url)
      .replace(/!\[([^\]]*)\]\(([^)\s]+)\)/g, function (_, alt, url) {
        return '<img src="' + url + '" alt="' + alt + '" loading="lazy">';
      })
      // 链接 [label](url)
      .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, function (_, label, url) {
        return '<a href="' + url + '" target="_blank" rel="noopener noreferrer">' + label + "</a>";
      })
      // 粗体
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      // 行内代码
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      // 斜体
      .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>");
  }

  function isTableSeparator(line) {
    return line.indexOf("|") !== -1 && /^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(line);
  }

  function splitRow(line) {
    return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(function (cell) {
      return cell.trim();
    });
  }

  var HEADING = /^\s*(#{1,6})\s+(.*)$/;
  var HR = /^\s*([-*_])\1{2,}\s*$/;
  var QUOTE = /^\s*>\s?/;
  var UL = /^\s*[-*+]\s+/;
  var OL = /^\s*\d+\.\s+/;
  var FENCE = /^\s*```/;

  function isBlockStart(line, nextLine) {
    return (
      FENCE.test(line) ||
      HEADING.test(line) ||
      HR.test(line) ||
      QUOTE.test(line) ||
      UL.test(line) ||
      OL.test(line) ||
      (nextLine !== undefined && line.indexOf("|") !== -1 && isTableSeparator(nextLine))
    );
  }

  function render(source) {
    var lines = escapeHtml(source == null ? "" : source).split(/\r?\n/);
    var html = [];
    var i = 0;

    while (i < lines.length) {
      var line = lines[i];

      // 代码块
      if (FENCE.test(line)) {
        var code = [];
        i++;
        while (i < lines.length && !FENCE.test(lines[i])) {
          code.push(lines[i]);
          i++;
        }
        i++;
        html.push("<pre><code>" + code.join("\n") + "</code></pre>");
        continue;
      }

      // 表格
      if (line.indexOf("|") !== -1 && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
        var header = splitRow(line);
        i += 2;
        var rows = [];
        while (i < lines.length && lines[i].trim() !== "" && lines[i].indexOf("|") !== -1) {
          rows.push(splitRow(lines[i]));
          i++;
        }
        var table = ["<table><thead><tr>"];
        header.forEach(function (cell) {
          table.push("<th>" + renderInline(cell) + "</th>");
        });
        table.push("</tr></thead><tbody>");
        rows.forEach(function (row) {
          table.push("<tr>");
          row.forEach(function (cell) {
            table.push("<td>" + renderInline(cell) + "</td>");
          });
          table.push("</tr>");
        });
        table.push("</tbody></table>");
        html.push(table.join(""));
        continue;
      }

      // 标题
      var heading = line.match(HEADING);
      if (heading) {
        var level = heading[1].length;
        html.push("<h" + level + ">" + renderInline(heading[2].trim()) + "</h" + level + ">");
        i++;
        continue;
      }

      // 分隔线
      if (HR.test(line)) {
        html.push("<hr>");
        i++;
        continue;
      }

      // 引用
      if (QUOTE.test(line)) {
        var quotes = [];
        while (i < lines.length && QUOTE.test(lines[i])) {
          quotes.push(lines[i].replace(QUOTE, ""));
          i++;
        }
        html.push("<blockquote>" + renderInline(quotes.join(" ")) + "</blockquote>");
        continue;
      }

      // 无序列表
      if (UL.test(line)) {
        var items = [];
        while (i < lines.length && UL.test(lines[i])) {
          items.push(lines[i].replace(UL, ""));
          i++;
        }
        html.push(
          "<ul>" +
            items
              .map(function (t) {
                return "<li>" + renderInline(t) + "</li>";
              })
              .join("") +
            "</ul>"
        );
        continue;
      }

      // 有序列表
      if (OL.test(line)) {
        var ordered = [];
        while (i < lines.length && OL.test(lines[i])) {
          ordered.push(lines[i].replace(OL, ""));
          i++;
        }
        html.push(
          "<ol>" +
            ordered
              .map(function (t) {
                return "<li>" + renderInline(t) + "</li>";
              })
              .join("") +
            "</ol>"
        );
        continue;
      }

      // 空行
      if (line.trim() === "") {
        i++;
        continue;
      }

      // 段落（连续非块级行合并）
      var paragraph = [];
      while (i < lines.length && lines[i].trim() !== "" && !isBlockStart(lines[i], lines[i + 1])) {
        paragraph.push(lines[i]);
        i++;
      }
      html.push("<p>" + renderInline(paragraph.join("<br>")) + "</p>");
    }

    return html.join("\n");
  }

  global.MarkdownRenderer = { render: render, escapeHtml: escapeHtml };
})(window);
