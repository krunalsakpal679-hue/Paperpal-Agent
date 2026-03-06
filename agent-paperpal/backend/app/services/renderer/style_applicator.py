# backend/app/services/renderer/style_applicator.py
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.style import WD_STYLE_TYPE
from app.schemas.jro_schema import JROSchema

class StyleApplicator:
    def build_document_styles(self, jro: JROSchema):
        """Builds a new docx Document and applies layout rules from JRO."""
        doc = Document()
        
        layout = jro.layout_rules
        font_name = layout.font_name or "Times New Roman"
        font_size = layout.font_size or 12
        line_spacing = layout.line_spacing or 1.0 # 1=single, 1.5=1.5 lines, 2=double

        # Apply normal style
        normal_style = doc.styles['Normal']
        normal_style.font.name = font_name
        normal_style.font.size = Pt(font_size)
        if hasattr(normal_style.paragraph_format, 'line_spacing'):
            normal_style.paragraph_format.line_spacing = line_spacing

        # Apply heading styles
        for i in range(1, 4):
            style_name = f'Heading {i}'
            if style_name in doc.styles:
                heading_style = doc.styles[style_name]
                heading_style.font.name = font_name
                heading_style.font.bold = True
                
                # Formula matching prompt:
                # Heading1: size = Normal + 8pt
                # Heading2: size = Normal + 4pt
                # Heading3: size = Normal + 2pt
                size_offset = {1: 8, 2: 4, 3: 2}.get(i, 0)
                heading_style.font.size = Pt(font_size + size_offset)
                
                if i == 1:
                    heading_style.paragraph_format.space_before = Pt(12) # ~240 DXA
                    heading_style.paragraph_format.space_after = Pt(6)   # ~120 DXA

        # Apply caption style
        if 'Caption' in doc.styles:
            caption_style = doc.styles['Caption']
            caption_style.font.name = font_name
            caption_style.font.italic = True
            caption_style.font.size = Pt(max(8, font_size - 2))
        else:
            caption_style = doc.styles.add_style('Caption', WD_STYLE_TYPE.PARAGRAPH)
            caption_style.font.name = font_name
            caption_style.font.italic = True
            caption_style.font.size = Pt(max(8, font_size - 2))

        # Set margins
        margins = layout.margins or {}
        for section in doc.sections:
            if 'top' in margins:
                section.top_margin = Inches(margins['top'])
            if 'bottom' in margins:
                section.bottom_margin = Inches(margins['bottom'])
            if 'left' in margins:
                section.left_margin = Inches(margins['left'])
            if 'right' in margins:
                section.right_margin = Inches(margins['right'])
            if 'header' in margins:
                section.header_distance = Inches(margins['header'])
            if 'footer' in margins:
                section.footer_distance = Inches(margins['footer'])

        return doc
