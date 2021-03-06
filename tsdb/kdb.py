import kydb
from qpython import qconnection
import pandas as pd
from .base import TimeSeries
from datetime import date, datetime
from typing import Union
from logging import getLogger

logger = getLogger(__name__)


class KDBTimeSeries(TimeSeries):

    @kydb.stored
    def table(self) -> str:
        return 't'

    @kydb.stored
    def host(self) -> str:
        return 'localhost'

    @kydb.stored
    def port(self) -> int:
        return 5001

    def curve(self,
              start_dt: Union[date, datetime],
              end_dt: Union[date, datetime]) -> pd.DataFrame:

        cmd = self.q_cmd(start_dt, end_dt)
        return self.q(cmd)

    def q(self, cmd: str) -> pd.DataFrame:
        """
        Execute q command on KDB+

        :param cmd: The q command to execute

Example:

Assume the remote KDB+ has a tbl with time and price as column.

Insert 100 random prices into a table

::

    tbl:([] time:100?.z.p; price:100?10f)

Using .curve(...) you could get a slice of that table.
However, if instead you want a 10 day moving average. You could always do this.

::

    ts.q('10 mavg tbl.price')

        """
        with qconnection.QConnection(host=self.host(), port=self.port()) as q:
            res = q(cmd)
            return pd.DataFrame.from_records(res)

    def q_cmd(self,
              start_dt: Union[date, datetime],
              end_dt: Union[date, datetime]) -> str:
        return 'select from {table} where dt>={start_dt},dt<={end_dt}'.format(
            table=self.table(),
            start_dt=start_dt.timestamp(),
            end_dt=end_dt.timestamp()
        )
