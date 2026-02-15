import logging

logger = logging.getLogger(__name__)

# Settings we care about for the audit
POSTGRESQL_CONF_SETTINGS = [
    'max_connections',
    'ssl',
    'ssl_cert_file',
    'ssl_key_file',
    'ssl_ca_file',
]


class PostgresServerSettingsInspector:
    """Queries live PostgreSQL server settings via pg_settings and pg_hba_file_rules."""

    def __init__(self, connection):
        self.connection = connection

    def get_current_settings(self):
        """Query pg_settings for the settings we recommend.

        Returns:
            dict of {setting_name: {'value': str, 'source': str}} on success,
            or None if permission was denied or an error occurred.
        """
        try:
            with self.connection.cursor() as cur:
                cur.execute(
                    "SELECT name, setting, source FROM pg_settings WHERE name = ANY(%s)",
                    (POSTGRESQL_CONF_SETTINGS,),
                )
                rows = cur.fetchall()

            result = {}
            for name, setting, source in rows:
                result[name] = {'value': setting, 'source': source}
            return result

        except Exception as e:
            error_msg = str(e).lower()
            if 'permission' in error_msg or 'privilege' in error_msg:
                logger.info("Insufficient privileges to query pg_settings: %s", e)
                print("\nNote: Could not query server settings (permission denied).")
                print("The connected role does not have access to pg_settings.")
            else:
                logger.info("Could not query pg_settings: %s", e)
                print(f"\nNote: Could not query server settings: {e}")
            return None

    def get_hba_rules(self):
        """Query pg_hba_file_rules for current HBA configuration.

        This view is available in PostgreSQL 15+. Returns None gracefully
        if the view doesn't exist or permission is denied.

        Returns:
            list of dicts on success, or None if unavailable.
        """
        try:
            with self.connection.cursor() as cur:
                cur.execute(
                    "SELECT line_number, type, database, user_name, address, "
                    "netmask, auth_method, options "
                    "FROM pg_hba_file_rules WHERE error IS NULL "
                    "ORDER BY line_number"
                )
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()

            return [dict(zip(columns, row)) for row in rows]

        except Exception as e:
            error_msg = str(e).lower()
            if 'permission' in error_msg or 'privilege' in error_msg:
                logger.info("Insufficient privileges to query pg_hba_file_rules: %s", e)
            elif 'does not exist' in error_msg or 'relation' in error_msg:
                logger.info("pg_hba_file_rules view not available (requires PostgreSQL 15+): %s", e)
            else:
                logger.info("Could not query pg_hba_file_rules: %s", e)
            return None

    def compare_settings(self, recommended):
        """Compare recommended settings against current live server settings.

        Args:
            recommended: list of strings like 'max_connections = 22', 'ssl = on', etc.

        Returns:
            list of dicts with keys: setting, recommended, current, source, status.
            Returns None if current settings could not be fetched.
        """
        current = self.get_current_settings()
        if current is None:
            return None

        comparisons = []
        for entry in recommended:
            if '=' not in entry:
                continue
            parts = entry.split('=', 1)
            setting_name = parts[0].strip()
            recommended_value = parts[1].strip().strip("'\"")

            current_info = current.get(setting_name)
            if current_info is None:
                comparisons.append({
                    'setting': setting_name,
                    'recommended': recommended_value,
                    'current': '(not found)',
                    'source': '',
                    'status': 'UNKNOWN',
                })
                continue

            current_value = current_info['value']
            source = current_info['source']

            status = self._evaluate_status(setting_name, recommended_value, current_value)
            comparisons.append({
                'setting': setting_name,
                'recommended': recommended_value,
                'current': current_value,
                'source': source,
                'status': status,
            })

        return comparisons

    @staticmethod
    def _evaluate_status(setting_name, recommended, current):
        """Determine if a setting matches the recommendation."""
        if setting_name == 'max_connections':
            try:
                if int(current) >= int(recommended):
                    return 'OK'
                else:
                    return 'MISMATCH'
            except (ValueError, TypeError):
                return 'UNKNOWN'

        if setting_name == 'ssl':
            if current.lower() == recommended.lower():
                return 'OK'
            return 'MISMATCH'

        # For file paths and other string settings
        if current.strip("'\"") == recommended.strip("'\""):
            return 'OK'

        return 'REVIEW'
