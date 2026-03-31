from __future__ import annotations

from typing import Iterable


def _escape_pdf_text(text: str) -> str:
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def build_pdf_briefing(
    project_name: str,
    status_narrative: str,
    leadership_summary: Iterable[str],
    top_actions: Iterable[str],
    top_risks: Iterable[str],
) -> bytes:
    lines = [
        project_name,
        '',
        'Executive Briefing',
        '',
        'Status narrative:',
        status_narrative,
        '',
        'Leadership summary:',
        *[f'- {item}' for item in leadership_summary],
        '',
        'Top actions:',
        *[f'- {item}' for item in top_actions],
        '',
        'Top risks:',
        *[f'- {item}' for item in top_risks],
    ]

    y = 780
    content_lines = ['BT', '/F1 12 Tf']
    for line in lines:
        safe = _escape_pdf_text(line[:110])
        content_lines.append(f'1 0 0 1 50 {y} Tm ({safe}) Tj')
        y -= 18
        if y < 60:
            break
    content_lines.append('ET')
    stream = '\n'.join(content_lines).encode('latin-1', errors='replace')

    objects = []
    objects.append(b'1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n')
    objects.append(b'2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n')
    objects.append(b'3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n')
    objects.append(f'4 0 obj << /Length {len(stream)} >> stream\n'.encode('latin-1') + stream + b'\nendstream endobj\n')
    objects.append(b'5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n')

    pdf = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_start = len(pdf)
    pdf.extend(f'xref\n0 {len(offsets)}\n'.encode('latin-1'))
    pdf.extend(b'0000000000 65535 f \n')
    for off in offsets[1:]:
        pdf.extend(f'{off:010d} 00000 n \n'.encode('latin-1'))
    pdf.extend(f'trailer << /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF'.encode('latin-1'))
    return bytes(pdf)
