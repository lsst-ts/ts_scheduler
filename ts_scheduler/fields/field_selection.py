try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest

class FieldSelection(object):
    """Class for constructing SQL queries on the survey fields database.

    This class is for creating SQL queries to perform on the survey fields database.
    It does not actually perform the queries.
    """

    def base_select(self):
        """Return the base field query.

        Returns
        -------
        str
        """
        return "select * from Field"

    def finish_query(self, query):
        """Put a semicolon at the end of a query.

        Parameters
        ----------
        query : str
            The SQL query to finish.

        Returns
        -------
        str
            The finished SQl query.
        """
        return query + ";"

    def combine_queries(self, combiners, *queries, **kwargs):
        """Combine a set of queries.

        Parameters
        ----------
        combiners : tuple of str
            A set of logical operations (and, or etc.) to join the queries with.
        queries : str instances
            A set of queries to join via the given operators.
        order_by : str, optional
            Set the order by clause. Default is fieldId.

        Returns
        -------
        str:
            The fully combined query.
        """
        if len(combiners) != len(queries) - 1:
            raise RuntimeError("Number of combiners must be one less than number of queries!")

        order_by = kwargs.get("order_by", "fieldId")

        final_query = []
        final_query.append(self.base_select())
        final_query.append("where")
        for combine, query in zip_longest(combiners, queries):
            final_query.append(query)
            if combine is not None:
                final_query.append(combine)
        final_query.append("order by {}".format(order_by))

        return self.finish_query(" ".join(final_query))

    def galactic_region(self, maxB, minB, endL, exclusion=True):
        """Create a galactic region.

        This function creates a sloping region around the galactic plane to either include or
        exclude fields.

        Parameters
        ----------
        maxB : float
            The maximum galactic latitude at the galacitc longitude of zero.
        minB : float
            The minimum galactic latitude at the galactic longitude of endL.
        endL : float
            The galactic longitude for the end of the envelope region.

        Returns
        -------
        str
            The appropriate query.
        """
        region_select = ">" if exclusion else "<="
        band = maxB - minB
        sql = '(abs(fieldGB) {0} ({1} - ({2} * abs(fieldGL)) / {3}))'.format(region_select,
                                                                             maxB, band, endL)

        return sql

    def select_region(self, region_type, start_value, end_value):
        """Create a simple bounded region.

        Parameters
        ----------

        Returns
        -------
        str
            The appropriate query.
        """
        if end_value > start_value:
            sql = '{0} between {1} and {2}'.format(region_type, start_value, end_value)
        else:
            sql = '({0} between {1} and 360 or {0} between 0 and {2})'.format(region_type, start_value,
                                                                              end_value)

        return sql
