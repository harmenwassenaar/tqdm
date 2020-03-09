"""
Thin wrappers around `concurrent.futures`.
"""
from __future__ import absolute_import
from tqdm.auto import tqdm as tqdm_auto
from copy import deepcopy
try:
    from os import cpu_count
except ImportError:
    try:
        from multiprocessing import cpu_count
    except ImportError:
        def cpu_count():
            return 4
try:
    from operator import length_hint
except ImportError:
    def length_hint(it, default=0):
        try:
            return len(it)
        except TypeError:
            return default
import sys
__author__ = {"github.com/": ["casperdcl"]}
__all__ = ['thread_map', 'process_map']


def _executor_map(PoolExecutor, fn, *iterables, **tqdm_kwargs):
    """
    Implementation of `thread_map` and `process_map`.
    """
    kwargs = deepcopy(tqdm_kwargs)
    if "total" not in kwargs:
        kwargs["total"] = len(iterables[0])
    tqdm_class = kwargs.pop("tqdm_class", tqdm_auto)
    max_workers = kwargs.pop("max_workers", min(32, cpu_count() + 4))
    chunksize = kwargs.pop("chunksize", 1)
    pool_kwargs = dict(max_workers=max_workers)
    if sys.version_info[:2] >= (3, 7):
        # share lock in case workers are already using `tqdm`
        pool_kwargs.update(
            initializer=tqdm_class.set_lock, initargs=(tqdm_class.get_lock(),))
    with PoolExecutor(**pool_kwargs) as ex:
        return list(tqdm_class(ex.map(fn, *iterables, chunksize=chunksize), **kwargs))


def thread_map(fn, *iterables, **tqdm_kwargs):
    """
    Equivalent of `list(map(fn, *iterables))`
    driven by `concurrent.futures.ThreadPoolExecutor`.

    Parameters
    ----------
    tqdm_class : optional
        `tqdm` class to use for bars [default: `tqdm.auto.tqdm`].
    max_workers : int, optional
        Maximum number of workers to spawn; passed to
        `concurrent.futures.ThreadPoolExecutor.__init__`.
        [default: max(32, cpu_count() + 4)].
    """
    from concurrent.futures import ThreadPoolExecutor
    return _executor_map(ThreadPoolExecutor, fn, *iterables, **tqdm_kwargs)


def process_map(fn, *iterables, **tqdm_kwargs):
    """
    Equivalent of `list(map(fn, *iterables))`
    driven by `concurrent.futures.ProcessPoolExecutor`.

    Parameters
    ----------
    tqdm_class  : optional
        `tqdm` class to use for bars [default: `tqdm.auto.tqdm`].
    max_workers : int, optional
        Maximum number of workers to spawn; passed to
        `concurrent.futures.ProcessPoolExecutor.__init__`.
        [default: max(32, cpu_count() + 4)].
    chunksize : int, optional
        Size of chunks sent to worker processes; passed to
        `concurrent.futures.ProcessPoolExecutor.map`.  [default: 1].
    """
    from concurrent.futures import ProcessPoolExecutor
    if iterables and "chunksize" not in tqdm_kwargs:
        # For large iterables, default chunksize has very bad performance
        # because most time is spent sending items to workers.
        longest_iterable_len = max(map(length_hint, iterables))
        if longest_iterable_len >= 1000:
            from warnings import warn
            warn(
                "Received iterable of length {} but 'chunksize' parameter is "
                "not set. This may seriously degrade multiprocess performance. "
                "To silence this warning, set 'chunksize' to a value >= 1.".format(longest_iterable_len),
                RuntimeWarning, stacklevel=2,
            )
    return _executor_map(ProcessPoolExecutor, fn, *iterables, **tqdm_kwargs)
