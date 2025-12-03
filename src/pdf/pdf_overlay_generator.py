"""Generate PDFs by overlaying text on template PDFs."""
from typing import Dict, Any
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PyPDF2 import PdfReader, PdfWriter, PdfMerger
from io import BytesIO
from loguru import logger
import yaml


class PDFOverlayGenerator:
    """Generate completed PDFs by overlaying data on static PDF templates."""

    def __init__(self, template_dir: Path, field_positions_dir: Path):
        """Initialize PDF overlay generator.

        Args:
            template_dir: Directory containing PDF templates
            field_positions_dir: Directory with YAML position configs
        """
        self.template_dir = Path(template_dir)
        self.field_positions_dir = Path(field_positions_dir)

    def generate_pdf(self,
                    template_name: str,
                    data: Dict[str, Any],
                    output_path: Path) -> bool:
        """Generate PDF by overlaying data on template.

        Args:
            template_name: Name of template (without .pdf)
            data: Dictionary of field values
            output_path: Path to save completed PDF

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load template PDF
            template_path = self.template_dir / f"{template_name}.pdf"
            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_path}")

            # Load field positions
            positions_path = self.field_positions_dir / f"{template_name}.yaml"
            if not positions_path.exists():
                raise FileNotFoundError(f"Position config not found: {positions_path}")

            with open(positions_path, 'r') as f:
                config = yaml.safe_load(f)

            logger.info(f"Generating PDF from template: {template_name}")

            # Read template
            template_reader = PdfReader(template_path)
            num_pages = len(template_reader.pages)

            # Create overlay for each page
            writer = PdfWriter()

            for page_num in range(num_pages):
                # Create overlay with text
                overlay_buffer = self._create_overlay(
                    page_num,
                    data,
                    config,
                    template_reader.pages[page_num]
                )

                if overlay_buffer:
                    # Merge overlay with template page
                    overlay_reader = PdfReader(overlay_buffer)
                    template_page = template_reader.pages[page_num]
                    template_page.merge_page(overlay_reader.pages[0])
                    writer.add_page(template_page)
                else:
                    # No overlay for this page, just add template
                    writer.add_page(template_reader.pages[page_num])

            # Write output
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

            logger.info(f"✓ Generated PDF: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to generate PDF: {e}")
            return False

    def _create_overlay(self,
                       page_num: int,
                       data: Dict[str, Any],
                       config: Dict[str, Any],
                       template_page) -> BytesIO:
        """Create text overlay for a single page.

        Args:
            page_num: Page number (0-indexed)
            data: Field data
            config: Position configuration
            template_page: Template page object

        Returns:
            BytesIO buffer with overlay PDF
        """
        # Get page size from template
        page_width = float(template_page.mediabox.width)
        page_height = float(template_page.mediabox.height)

        # Create overlay canvas
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=(page_width, page_height))

        # Get fields for this page
        page_fields = config.get('pages', {}).get(page_num, {})

        if not page_fields:
            # No fields on this page
            return None

        # Draw each field
        for field_name, field_config in page_fields.items():
            value = data.get(field_name, '')

            if value:
                x = field_config.get('x', 0)
                y = field_config.get('y', 0)
                font_name = field_config.get('font', 'Helvetica')
                font_size = field_config.get('size', 10)
                max_width = field_config.get('max_width', None)

                # Set font
                c.setFont(font_name, font_size)

                # Draw text
                if max_width:
                    # Wrap text if max_width specified
                    self._draw_wrapped_text(c, str(value), x, y, max_width, font_size)
                else:
                    c.drawString(x, y, str(value))

        c.save()
        buffer.seek(0)
        return buffer

    def _draw_wrapped_text(self, canvas_obj, text: str, x: float, y: float,
                          max_width: float, font_size: float):
        """Draw text with word wrapping.

        Args:
            canvas_obj: ReportLab canvas
            text: Text to draw
            x: X coordinate
            y: Y coordinate
            max_width: Maximum width in points
            font_size: Font size
        """
        words = text.split()
        lines = []
        current_line = []

        for word in words:
            current_line.append(word)
            line_text = ' '.join(current_line)

            # Check if line exceeds max width
            if canvas_obj.stringWidth(line_text) > max_width:
                if len(current_line) > 1:
                    # Remove last word and start new line
                    current_line.pop()
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    # Single word exceeds width, add anyway
                    lines.append(line_text)
                    current_line = []

        # Add remaining words
        if current_line:
            lines.append(' '.join(current_line))

        # Draw lines
        for i, line in enumerate(lines):
            canvas_obj.drawString(x, y - (i * font_size * 1.2), line)
