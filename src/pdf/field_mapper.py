"""Field mapping between database and PDF forms."""
from typing import Dict, Any
from pathlib import Path
import yaml
from loguru import logger
from datetime import datetime


class FieldMapper:
    """Maps database fields to PDF form fields using YAML configs."""

    def __init__(self, mappings_dir: Path):
        """Initialize field mapper.

        Args:
            mappings_dir: Directory containing YAML mapping files
        """
        self.mappings_dir = Path(mappings_dir)
        self.mappings_cache = {}

    def get_mapping(self, template_name: str) -> Dict[str, Any]:
        """Load field mapping for a template.

        Args:
            template_name: Name of template (e.g., 'progress_note')

        Returns:
            Dictionary with field mappings
        """
        if template_name in self.mappings_cache:
            return self.mappings_cache[template_name]

        mapping_path = self.mappings_dir / f"{template_name}.yaml"
        if not mapping_path.exists():
            raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

        with open(mapping_path, 'r') as f:
            mapping = yaml.safe_load(f)

        self.mappings_cache[template_name] = mapping
        logger.info(f"Loaded field mapping: {template_name} ({len(mapping.get('fields', {}))} fields)")
        return mapping

    def map_data_to_fields(self,
                          field_map: Dict[str, Any],
                          patient_data: Dict[str, Any],
                          visit_data: Dict[str, Any]) -> Dict[str, str]:
        """Map database records to PDF form fields.

        Args:
            field_map: YAML mapping configuration
            patient_data: Patient demographics
            visit_data: Visit/note details

        Returns:
            Dictionary of {pdf_field_name: value}
        """
        pdf_fields = {}
        combined_data = {**patient_data, **visit_data}

        for pdf_field, db_config in field_map.get('fields', {}).items():
            # Extract field configuration
            db_field = db_config.get('source')
            transform = db_config.get('transform')
            default = db_config.get('default', '')

            # Get value from database
            value = combined_data.get(db_field, default)

            # Apply transformation if specified
            if transform and value:
                value = self._apply_transform(value, transform)

            # Convert to string for PDF
            pdf_fields[pdf_field] = str(value) if value is not None else ''

        logger.debug(f"Mapped {len(pdf_fields)} fields to PDF form")
        return pdf_fields

    def _apply_transform(self, value: Any, transform: str) -> Any:
        """Apply transformation to field value.

        Args:
            value: Original value
            transform: Transform type (date_format, upper, lower, etc.)

        Returns:
            Transformed value
        """
        if transform.startswith('date:'):
            # Date formatting: date:MM/DD/YYYY
            format_str = transform.split(':', 1)[1]
            if isinstance(value, str):
                # Parse various date formats
                for fmt in ['%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y', '%B %d, %Y']:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return dt.strftime(format_str)
                    except:
                        continue
            return value

        elif transform == 'upper':
            return value.upper() if isinstance(value, str) else value

        elif transform == 'lower':
            return value.lower() if isinstance(value, str) else value

        elif transform.startswith('truncate:'):
            # Truncate to length: truncate:100
            max_len = int(transform.split(':', 1)[1])
            return value[:max_len] if isinstance(value, str) else value

        return value
