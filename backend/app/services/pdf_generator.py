"""
PDF Report Generator - Professional PDF generation using ReportLab.
Provides styled reports for GMAO system with headers, tables, and summaries.
Enhanced with proper text wrapping and better spacing to prevent clipping.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# Color palette for consistent branding
class ReportColors:
    """Color scheme for professional reports"""
    PRIMARY = colors.HexColor('#3b82f6')  # Blue
    PRIMARY_DARK = colors.HexColor('#1e40af')
    SECONDARY = colors.HexColor('#6366f1')  # Indigo
    SUCCESS = colors.HexColor('#10b981')  # Green
    WARNING = colors.HexColor('#f59e0b')  # Amber
    DANGER = colors.HexColor('#ef4444')  # Red
    GRAY_50 = colors.HexColor('#f9fafb')
    GRAY_100 = colors.HexColor('#f3f4f6')
    GRAY_200 = colors.HexColor('#e5e7eb')
    GRAY_400 = colors.HexColor('#9ca3af')
    GRAY_600 = colors.HexColor('#4b5563')
    GRAY_800 = colors.HexColor('#1f2937')
    WHITE = colors.white


class PDFReportGenerator:
    """
    Professional PDF report generator for GMAO system.
    Creates management-ready reports with consistent styling.
    Uses proper text wrapping to prevent clipping issues.
    """
    
    # Page dimensions
    PAGE_WIDTH = A4[0] - 100  # Account for margins (50 each side)
    
    def __init__(self, title: str, subtitle: Optional[str] = None):
        """
        Initialize report generator.
        
        Args:
            title: Main report title
            subtitle: Optional subtitle (e.g., date range)
        """
        self.title = title
        self.subtitle = subtitle
        self.buffer = BytesIO()
        self.elements = []
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
        
    def _setup_custom_styles(self):
        """Define custom paragraph styles with proper leading for text wrapping"""
        
        def add_or_update_style(style):
            if style.name in self.styles.byName:
                self.styles.byName[style.name] = style
            else:
                self.styles.add(style)
        
        # Title style
        add_or_update_style(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=22,
            leading=28,  # Line height
            textColor=ReportColors.GRAY_800,
            spaceAfter=8,
            spaceBefore=0,
            alignment=TA_CENTER
        ))
        
        # Subtitle style
        add_or_update_style(ParagraphStyle(
            name='ReportSubtitle',
            parent=self.styles['Normal'],
            fontSize=11,
            leading=14,
            textColor=ReportColors.GRAY_600,
            spaceAfter=15,
            alignment=TA_CENTER
        ))
        
        # Section heading
        add_or_update_style(ParagraphStyle(
            name='SectionHeading',
            parent=self.styles['Heading2'],
            fontSize=13,
            leading=18,
            textColor=ReportColors.PRIMARY_DARK,
            spaceBefore=25,
            spaceAfter=8,
            fontName='Helvetica-Bold'
        ))
        
        # Subsection heading  
        add_or_update_style(ParagraphStyle(
            name='SubsectionHeading',
            parent=self.styles['Heading3'],
            fontSize=11,
            leading=14,
            textColor=ReportColors.GRAY_800,
            spaceBefore=15,
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))
        
        # KPI value style - larger for impact
        add_or_update_style(ParagraphStyle(
            name='KpiValue',
            parent=self.styles['Normal'],
            fontSize=20,
            leading=26,
            textColor=ReportColors.PRIMARY,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # KPI label style
        add_or_update_style(ParagraphStyle(
            name='KpiLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=ReportColors.GRAY_600,
            alignment=TA_CENTER
        ))
        
        # Table cell text - with word wrap support
        add_or_update_style(ParagraphStyle(
            name='TableCell',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=11,
            textColor=ReportColors.GRAY_800,
            wordWrap='CJK'  # Enable word wrap
        ))
        
        # Table header text
        add_or_update_style(ParagraphStyle(
            name='TableHeader',
            parent=self.styles['Normal'],
            fontSize=9,
            leading=12,
            textColor=ReportColors.WHITE,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER
        ))
        
        # Description/body text
        add_or_update_style(ParagraphStyle(
            name='BodyText',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=ReportColors.GRAY_800,
            spaceBefore=4,
            spaceAfter=8
        ))
        
        # Note/small text
        add_or_update_style(ParagraphStyle(
            name='NoteText',
            parent=self.styles['Normal'],
            fontSize=8,
            leading=10,
            textColor=ReportColors.GRAY_600,
            fontName='Helvetica-Oblique'
        ))
        
    def add_header(self):
        """Add report header with title, subtitle and generation info"""
        # Company/System identifier
        self.elements.append(Paragraph(
            "PROACT - GMAO System",
            self.styles['NoteText']
        ))
        self.elements.append(Spacer(1, 5))
        
        # Title
        self.elements.append(Paragraph(self.title, self.styles['ReportTitle']))
        
        # Subtitle if provided
        if self.subtitle:
            self.elements.append(Paragraph(self.subtitle, self.styles['ReportSubtitle']))
        
        # Horizontal line
        self.elements.append(HRFlowable(
            width="100%",
            thickness=2,
            color=ReportColors.PRIMARY,
            spaceBefore=5,
            spaceAfter=15
        ))
        
        # Generation timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y à %H:%M")
        self.elements.append(Paragraph(
            f"<i>Rapport généré le {timestamp}</i>",
            self.styles['NoteText']
        ))
        self.elements.append(Spacer(1, 20))
        
    def add_section(self, title: str, description: Optional[str] = None):
        """Add a section heading with optional description"""
        self.elements.append(Paragraph(title, self.styles['SectionHeading']))
        self.elements.append(HRFlowable(
            width="100%",
            thickness=1,
            color=ReportColors.GRAY_200,
            spaceBefore=0,
            spaceAfter=8
        ))
        if description:
            self.elements.append(Paragraph(description, self.styles['BodyText']))
        
    def add_subsection(self, title: str):
        """Add a subsection heading"""
        self.elements.append(Paragraph(title, self.styles['SubsectionHeading']))
        
    def add_kpi_row(self, kpis: List[Dict[str, Any]]):
        """
        Add a row of KPI cards with proper spacing.
        
        Args:
            kpis: List of dicts with 'value', 'label', and optional 'color', 'description'
        """
        if not kpis:
            return
            
        # Create KPI cells with Paragraph wrapping for proper text handling
        kpi_cells = []
        for kpi in kpis:
            value = kpi.get('value', 'N/A')
            label = kpi.get('label', '')
            description = kpi.get('description', '')
            
            # Build cell content as nested table for better control
            cell_content = []
            cell_content.append(Paragraph(str(value), self.styles['KpiValue']))
            cell_content.append(Spacer(1, 4))
            cell_content.append(Paragraph(label, self.styles['KpiLabel']))
            if description:
                cell_content.append(Spacer(1, 2))
                cell_content.append(Paragraph(
                    f"<font size='7' color='#9ca3af'>{description}</font>", 
                    self.styles['NoteText']
                ))
            kpi_cells.append(cell_content)
        
        # Calculate column widths - equal distribution
        num_kpis = len(kpis)
        col_width = (self.PAGE_WIDTH - (num_kpis - 1) * 5) / num_kpis  # 5pt gap between columns
        
        # Create table for KPIs
        table = Table([kpi_cells], colWidths=[col_width] * num_kpis)
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOX', (0, 0), (-1, -1), 1, ReportColors.GRAY_200),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, ReportColors.GRAY_200),
            ('BACKGROUND', (0, 0), (-1, -1), ReportColors.GRAY_50),
            ('TOPPADDING', (0, 0), (-1, -1), 15),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 20))
        
    def add_table(
        self,
        headers: List[str],
        data: List[List[Any]],
        col_widths: Optional[List[float]] = None,
        zebra_stripe: bool = True,
        wrap_text: bool = True
    ):
        """
        Add a data table with professional styling and text wrapping.
        
        Args:
            headers: Column headers
            data: 2D list of data rows
            col_widths: Optional column widths (in points)
            zebra_stripe: Alternate row colors
            wrap_text: Enable text wrapping in cells (prevents clipping)
        """
        if not data:
            self.elements.append(Paragraph(
                "<i>Aucune donnée disponible</i>",
                self.styles['BodyText']
            ))
            return
        
        # Convert all cells to Paragraphs for proper text wrapping
        if wrap_text:
            # Header row with styled Paragraphs
            styled_headers = [
                Paragraph(str(h), self.styles['TableHeader']) for h in headers
            ]
            # Data rows with styled Paragraphs
            styled_data = []
            for row in data:
                styled_row = [
                    Paragraph(str(cell) if cell else '', self.styles['TableCell']) 
                    for cell in row
                ]
                styled_data.append(styled_row)
            table_data = [styled_headers] + styled_data
        else:
            table_data = [headers] + data
        
        # Calculate column widths if not provided
        if col_widths is None:
            num_cols = len(headers)
            col_widths = [self.PAGE_WIDTH / num_cols] * num_cols
        
        # Create table with repeatRows for multi-page tables
        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        
        # Base style
        style = [
            # Header styling
            ('BACKGROUND', (0, 0), (-1, 0), ReportColors.PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            
            # Data styling
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            
            # Grid
            ('BOX', (0, 0), (-1, -1), 1, ReportColors.GRAY_200),
            ('LINEBELOW', (0, 0), (-1, 0), 2, ReportColors.PRIMARY_DARK),
            ('INNERGRID', (0, 1), (-1, -1), 0.5, ReportColors.GRAY_200),
        ]
        
        # Add zebra striping
        if zebra_stripe:
            for i in range(1, len(table_data)):
                if i % 2 == 0:
                    style.append(('BACKGROUND', (0, i), (-1, i), ReportColors.GRAY_50))
        
        table.setStyle(TableStyle(style))
        self.elements.append(table)
        self.elements.append(Spacer(1, 15))
        
    def add_summary_box(self, title: str, items: List[Tuple[str, Any]], two_columns: bool = False):
        """
        Add a summary box with key-value pairs.
        
        Args:
            title: Box title
            items: List of (label, value) tuples
            two_columns: Split items into two columns
        """
        self.elements.append(Paragraph(f"<b>{title}</b>", self.styles['BodyText']))
        self.elements.append(Spacer(1, 6))
        
        if two_columns and len(items) > 2:
            # Split into two columns
            mid = (len(items) + 1) // 2
            left_items = items[:mid]
            right_items = items[mid:]
            
            # Create two-column table
            max_rows = max(len(left_items), len(right_items))
            table_data = []
            for i in range(max_rows):
                row = []
                if i < len(left_items):
                    row.extend([
                        Paragraph(left_items[i][0], self.styles['TableCell']),
                        Paragraph(str(left_items[i][1]), self.styles['TableCell'])
                    ])
                else:
                    row.extend(['', ''])
                if i < len(right_items):
                    row.extend([
                        Paragraph(right_items[i][0], self.styles['TableCell']),
                        Paragraph(str(right_items[i][1]), self.styles['TableCell'])
                    ])
                else:
                    row.extend(['', ''])
                table_data.append(row)
            
            col_width = (self.PAGE_WIDTH - 20) / 4
            table = Table(table_data, colWidths=[col_width * 1.3, col_width * 0.7, col_width * 1.3, col_width * 0.7])
        else:
            # Single column layout
            data = [
                [
                    Paragraph(label, self.styles['TableCell']), 
                    Paragraph(str(value), self.styles['TableCell'])
                ] 
                for label, value in items
            ]
            table = Table(data, colWidths=[self.PAGE_WIDTH * 0.55, self.PAGE_WIDTH * 0.45])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), ReportColors.GRAY_100),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOX', (0, 0), (-1, -1), 1, ReportColors.GRAY_200),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, ReportColors.GRAY_200),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 15))
    
    def add_info_box(self, content: str, box_type: str = 'info'):
        """
        Add an information/warning box.
        
        Args:
            content: Box content text
            box_type: 'info', 'warning', 'success', 'danger'
        """
        color_map = {
            'info': (ReportColors.PRIMARY, colors.HexColor('#dbeafe')),
            'warning': (ReportColors.WARNING, colors.HexColor('#fef3c7')),
            'success': (ReportColors.SUCCESS, colors.HexColor('#d1fae5')),
            'danger': (ReportColors.DANGER, colors.HexColor('#fee2e2'))
        }
        border_color, bg_color = color_map.get(box_type, color_map['info'])
        
        table_data = [[Paragraph(content, self.styles['BodyText'])]]
        table = Table(table_data, colWidths=[self.PAGE_WIDTH])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), bg_color),
            ('BOX', (0, 0), (-1, -1), 2, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ]))
        
        self.elements.append(table)
        self.elements.append(Spacer(1, 15))
        
    def add_page_break(self):
        """Add a page break"""
        self.elements.append(PageBreak())
        
    def add_text(self, text: str, style: str = 'BodyText'):
        """Add a paragraph of text"""
        self.elements.append(Paragraph(text, self.styles[style]))
        self.elements.append(Spacer(1, 8))
        
    def add_spacer(self, height: float = 15):
        """Add vertical space"""
        self.elements.append(Spacer(1, height))
        
    def _add_page_number(self, canvas, doc):
        """Add page number and footer to each page"""
        page_num = canvas.getPageNumber()
        canvas.saveState()
        
        # Footer line
        canvas.setStrokeColor(ReportColors.GRAY_200)
        canvas.line(50, 40, A4[0] - 50, 40)
        
        # Page number - right aligned
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(ReportColors.GRAY_600)
        canvas.drawRightString(A4[0] - 50, 28, f"Page {page_num}")
        
        # Report title - left aligned
        canvas.drawString(50, 28, self.title[:50] + ('...' if len(self.title) > 50 else ''))
        
        canvas.restoreState()
        
    def generate(self, landscape_mode: bool = False) -> bytes:
        """
        Generate the PDF report.
        
        Args:
            landscape_mode: Use landscape orientation
            
        Returns:
            PDF file as bytes
        """
        page_size = landscape(A4) if landscape_mode else A4
        
        # Update page width for landscape
        if landscape_mode:
            self.PAGE_WIDTH = page_size[0] - 100
        
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=page_size,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=60
        )
        
        try:
            doc.build(self.elements, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        except Exception as e:
            logger.error(f"PDF generation error: {e}")
            raise
        
        self.buffer.seek(0)
        return self.buffer.getvalue()
