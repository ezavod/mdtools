# This file is part of MDTools.
# Copyright (C) 2021, The MDTools Development Team and all contributors
# listed in the file AUTHORS.rst
#
# MDTools is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# MDTools is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with MDTools.  If not, see <http://www.gnu.org/licenses/>.


"""
Functions for file input/output handling

This module can be called from :mod:`mdtools` via the shortcut ``fh``::

    import mdtools as mdt
    mdt.fh  # insetad of mdt.file_handler

"""


# Standard libraries
import os
import warnings
from datetime import datetime
# Third party libraries
import numpy as np
# Local application/library specific imports
import mdtools as mdt


def cd_up(n, path=__file__):
    """
    Move `n` steps upwards in the directory tree.
    
    Parameters
    ----------
    n : int
        Number of steps to go up in the directory tree.
    path : str, optional
        Directory or file to use as start.  Default: Position of the
        file from which this function is called (``__file__``)
    
    Returns
    -------
    p : str
        The `n`-th parent directory of `path`.
    """
    p = os.path.abspath(path)
    for i in range(n):
        p = os.path.dirname(p)
    return p


def backup(fname):
    """
    Backup a file by renaming it.
    
    Check if a file with name `fname` already exists.  If so, rename it
    to ``'fname.bak_timestamp'``, where ``'timestamp'`` is the time when
    the renaming was done in YYYY-MM-DD_HH-MM-SS format.
    
    Parameters
    ----------
    fname : str
        The filename of the file to backup.
    
    Returns
    -------
    renamed : bool
        Returns ``True`` if a file called `fname` already existed and
        was renamed.  ``False`` if no file called `fname` exists and no
        backup was done.
    """
    if os.path.isfile(fname):
        timestamp = datetime.now()
        backup_name = (fname + ".bak_" +
                       str(timestamp.strftime('%Y-%m-%d_%H-%M-%S')))
        os.rename(fname, backup_name)
        print("Backuped {} to {}".format(fname, backup_name))
        return True
    else:
        return False


def indent(text, amount, char=" "):
    r"""
    Indent a text by a given amount.
    
    Pad every line of `text` with as many instances of `char` as given
    by `amount`.  Lines in `text` are identified by Python's string
    method :meth:`str.splitlines`.
    
    Parameters
    ----------
    text : str
        String to be indented.
    amount : int
        Pad every line of `text` by this many instances of `char`.
        Negative values are treated as zero.
    char : str, optional
        The string to be used as padding.
    
    Returns
    -------
    indented_text : str
        The input text with every line padded by the given amount of
        padding characters.
    
    Examples
    --------
    >>> s = "Hello, World!\n  It's me, Mario!"
    >>> print(s)
    Hello, World!
      It's me, Mario!
    >>> print(mdt.fh.indent(s, amount=4))
        Hello, World!
          It's me, Mario!
    >>> print(mdt.fh.indent(s, amount=1, char="# "))
    # Hello, World!
    #   It's me, Mario!
    """
    padding = amount * char
    return ''.join(padding + line
                   for line in text.splitlines(keepends=True))


def header_str():
    """
    Create a standard header string for text files.
    
    The string can be printed directly to standard output using
    :func:`print`.
    
    The header string contains:
        
        * The date and time the text file was created (actually this
          function was called).
        * The MDTools copyright notice.
        * The information generated by
          :func:`mdtools.run_time_info.run_time_info`.
    
    Returns
    -------
    header : str
        Human readable string containing the above listed content.
    
    See Also
    --------
    :func:`mdtools.run_time_info.run_time_info` :
        Generate some run time information
    :func:`mdtools.run_time_info.run_time_info_str` :
        Create a string containing some run time information
    """
    timestamp = datetime.now()
    script, command_line, cwd, exe, version, pversion = mdt.rti.run_time_info()
    header = ("Created by {} on {}\n"
              .format(script, timestamp.strftime('%Y/%m/%d %H:%M')))
    header += "\n"
    header += mdt.__copyright_notice__ + "\n"
    header += "\n"
    header += "\n"
    header += "Command line input:\n"
    header += "  {}\n".format(command_line)
    header += "Working directory:\n"
    header += "  {}\n".format(cwd)
    header += "Executable:\n"
    header += "  {}\n".format(exe)
    header += "mdtools version:\n"
    header += "  {}\n".format(version)
    header += "Python version:\n"
    header += "  {}\n".format(pversion)
    return header


def write_header(fname, rename=True):
    """
    Create a file and write the standard MDTools header to it.
    
    See :func:`mdtools.file_handler.header_str` for further information
    about what is contained in the header.
    
    Parameters
    ----------
    fname : str
        The name of the file to create and to which to write the header.
    rename : bool, optional
        If ``True`` and a file called `fname` already exists, rename it
        to ``'fname.bak_timestamp'``.  See
        :func:`mdtools.file_handler.backup` for more details.
    
    See Also
    --------
    :func:`mdtools.file_handler.header_str` :
        Create a standard header string for text files
    :func:`mdtools.file_handler.backup` : Backup a file by renaming it
    """
    if rename:
        backup(fname)
    with open(fname, 'w') as outfile:
        outfile.write(indent(text=header_str(), amount=1, char="# "))


def savetxt(  # TODO: Replace arguments by *args, **kwargs
        fname, data, fmt='%16.9e', delimiter=' ', newline='\n',
        header='', footer='', comments='# ', encoding=None, rename=True):
    """
    Save an array to a text file.
    
    Parameters
    ----------
    fname : str
        The name of the file to create.
    data : array_like
        1- or 2-dimensional array of data to be saved.
    fmt : str or sequence of strs, optional
        Format specifier.  See :func:`numpy.savetxt` for more details.
    delimiter : str, optional
        String or character separating columns.
    newline : str, optional
        String or character separating lines.
    header : str, optional
        String that will be written at the beginning of the file,
        additional to the standard MDTools header.  See
        :func:`mdtools.file_handler.header_str` for more details.
    footer : str, optional
        String that will be written at the end of the file.
    comments : str, optional
        String that will be prepended to the header and footer strings,
        to mark them as comments.
    encoding : {None, str}, optional
        Encoding used to encode the outputfile.  Does not apply to
        output streams.  See documentation of :func:`numpy.savetxt`.
    rename : bool, optional
        If ``True`` and a file called `fname` already exists, rename it
        to ``'fname.bak_timestamp'``.  See
        :func:`mdtools.file_handler.backup` for more details.
    
    See Also
    --------
    :func:`numpy.savetxt` : Save an array to a text file
    :func:`mdtools.file_handler.savetxt_matrix` :
        Save a data matrix to a text file
    :func:`mdtools.file_handler.header_str` :
        Create a standard header string for text files
    :func:`mdtools.file_handler.backup` : Backup a file by renaming it
    
    Notes
    -----
    This function simply calls :func:`numpy.savetxt` and adds a
    MDTools specific header to the output file.  See
    :func:`mdtools.file_handler.header_str` for further information
    about what is included in the header.
    """
    head = header_str()
    if header is not None and header != '':
        head += "\n\n" + header
    if rename:
        backup(fname)
    np.savetxt(fname=fname,
               X=data,
               fmt=fmt,
               delimiter=delimiter,
               newline=newline,
               header=head,
               footer=footer,
               comments=comments,
               encoding=encoding)


def savetxt_matrix(  # TODO: Replace arguments by *args, **kwargs
        fname, data, var1, var2, init_values1=None, init_values2=None,
        upper_left=0, fmt='%16.9e', delimiter=' ', newline='\n',
        header='', footer='', comments='# ', encoding=None, rename=True):
    """
    Save a data matrix to a text file.
    
    Write data that are a function of two independent variables, `var1`
    and `var2`, as a matrix to a text file using
    :func:`mdtools.file_handler.savetxt`.  The dependency of the data
    from `var1` is represented by the rows and the dependency from
    `var2` is represented by the columns.
    
    Parameters
    ----------
    fname : str
        The name of the file to create.
    data : array_like
        2-dimensional array of data to be saved.  Must be of shape
        ``(n, m)``, where ``n`` is the number of samples of the first
        independent variable (depicted row wise) and ``m`` is the mumber
        of samples of the second independent variable (depicted column
        wise).
    var1 : array_like
        Array of shape ``(n,)`` containing the values of the first
        independent variable at which the data were sampled.
    var2 : array_like
        Array of shape ``(m,)`` containing the values of the second
        independent variable at which the data were sampled.
    init_values1 : array_like
        If supplied, the values stored in this array will be handled as
        special initial data values corresponding to the very first
        value in `var1`.  Must be an array of shape ``(m,)``, whereas
        `data` must then be of shape ``(n-1, m)``.
    init_values2 : array_like
        If supplied, the values stored in this array will be handled as
        special initial data values corresponding to the very first
        value in `var2`.  Must be an array of shape ``(n,)``, whereas
        `data` must then be of shape ``(n, m-1)``.
    upper_left : scalar
        Value to put in the upper left corner of the final data matrix.
        Usually, this value is meaningless and set to zero.
    fmt : str or sequence of strs, optional
        Format specifier.  See :func:`mdtools.file_handler.savetxt` for
        more details.
    delimiter : str, optional
        String or character separating columns.
    newline : str, optional
        String or character separating lines.
    header : str, optional
        String that will be written at the beginning of the file,
        additional to the standard MDTools header.  See
        :func:`mdtools.file_handler.header_str` for more details.
    footer : str, optional
        String that will be written at the end of the file.
    comments : str, optional
        String that will be prepended to the header and footer strings,
        to mark them as comments.
    encoding : {None, str}, optional
        Encoding used to encode the outputfile.  Does not apply to
        output streams.  See :func:`mdtools.file_handler.savetxt` for
        more details.
    rename : bool, optional
        If ``True`` and a file called `fname` already exists, rename it
        to ``'fname.bak_timestamp'``.  See
        :func:`mdtools.file_handler.backup` for more details.
    
    See Also
    --------
    :func:`mdtools.file_handler.savetxt` : Save an array to a text file
    :func:`mdtools.file_handler.write_matrix_block` :
        Save a data matrix to a text file by appending the file
    :func:`mdtools.file_handler.backup` : Backup a file by renaming it
    
    Notes
    -----
    Internally, this function calls :func:`mdtools.file_handler.savetxt`.
    """
    var1 = np.asarray(var1)
    var2 = np.asarray(var2)
    mdt.check.array(var1, dim=1)
    mdt.check.array(var2, dim=1)
    if init_values1 is None and init_values2 is None:
        mdt.check.array(data, shape=(len(var1), len(var2)))
    elif init_values1 is not None and init_values2 is None:
        mdt.check.array(init_values1, shape=var2.shape)
        mdt.check.array(data, shape=(len(var1)-1, len(var2)))
        data = np.vstack((init_values1, data))
    elif init_values1 is None and init_values2 is not None:
        mdt.check.array(init_values2, shape=var1.shape)
        mdt.check.array(data, shape=(len(var1), len(var2)-1))
        data = np.column_stack((init_values2, data))
    elif init_values1 is not None and init_values2 is not None:
        mdt.check.array(init_values1, shape=var2.shape)
        mdt.check.array(init_values2, shape=var1.shape)
        mdt.check.array(data, shape=(len(var1)-1, len(var2)-1))
        if init_values2[0] != init_values1[0]:
            warnings.warn("init_values2[0] ({}) is not the same as"
                          " init_values1[0] ({}). Using init_values1[0]"
                          " as value for the upper left corner."
                          .format(init_values2[0], init_values1[0]),
                          RuntimeWarning)
        data = np.column_stack((init_values2[1:], data))
        data = np.vstack((init_values1, data))
    data = np.column_stack((var1, data))
    var2 = np.insert(var2, 0, upper_left)
    data = np.vstack((var2, data))
    savetxt(fname=fname,
            data=data,
            fmt=fmt,
            delimiter=delimiter,
            newline=newline,
            header=header,
            footer=footer,
            comments=comments,
            encoding=encoding,
            rename=rename)


def write_matrix_block(
        fname, data, var1, var2, init_values1=None, init_values2=None,
        upper_left=None, data_name=None, data_unit=None, var1_name=None,
        var1_unit=None, var2_name=None, var2_unit=None,
        block_number=None):
    """
    Save a data matrix to a text file.
    
    Write data that are a function of two independent variables, `var1`
    and `var2`, as a matrix to a text file.  The dependency of the data
    from `var1` is represented by the rows and the dependency from `var2`
    is represented by the columns.
    
    If the file already exists, it is appended.  Otherwise is is created.
    
    Parameters
    ----------
    fname : str
        The name of the file to write to.  The file is created if it
        does not exist, otherwise it is appended.
    data : array_like
        The data to write to file.  Must be of shape ``(n, m)``, where
        ``n`` is the number of samples of the first independent variable
        (depicted row wise) and ``m`` is the mumber of samples of the
        second independent variable (depicted column wise).
    var1 : array_like
        Array of shape ``(n,)`` containing the values of the first
        independent variable.
    var2 : array_like
        Array of shape ``(m,)`` containing the values of the second
        independent variable.
    init_values1 : array_like
        If supplied, the values stored in this array will be handled as
        special initial data values corresponding to the very first
        value in `var1`.  Must be an array of shape ``(m,)``, whereas
        `data` must then be of shape ``(n-1, m)``.
    init_values2 : array_like
        If supplied, the values stored in this array will be handled as
        special initial data values corresponding to the very first
        value in `var2`.  Must be an array of shape ``(n,)``, whereas
        `data` must then be of shape ``(n, m-1)``.
    upper_left : scalar
        Value to put in the upper left corner of the final matrix.  If
        ``None`` (default), print `var1_name` and `var2_name` in the
        upper left corner.
    data_name : str
        The name of the data.  If supplied, it will be printed in the
        block header.
    data_unit : str
        The unit of the data.  If supplied, will be printed in the
        block header.
    var1_name : str
        Same as `data_name` but for `var1`.
    var1_unit : str
        Same as `data_unit` but for `var1`.
    var2_name : str
        Same as `data_name` but for `var2`.
    var2_unit : str
        Same as `data_unit` but for `var2`.
    block_number : int
        The number of the data block in `fname`.  If supplied, it will
        be printed in the block header.
    
    See Also
    --------
    :func:`mdtools.file_handler.savetxt_matrix` :
        Save a data matrix to a text file
    :func:`mdtools.file_handler.write_header` :
        Create a file and write the standard MDTools header to it
    """
    var1 = np.asarray(var1)
    var2 = np.asarray(var2)
    mdt.check.array(var1, dim=1)
    mdt.check.array(var2, dim=1)
    if init_values1 is None and init_values2 is None:
        mdt.check.array(data, shape=(len(var1), len(var2)))
    elif init_values1 is not None and init_values2 is None:
        mdt.check.array(init_values1, shape=var2.shape)
        mdt.check.array(data, shape=(len(var1)-1, len(var2)))
    elif init_values1 is None and init_values2 is not None:
        mdt.check.array(init_values2, shape=var1.shape)
        mdt.check.array(data, shape=(len(var1), len(var2)-1))
    elif init_values1 is not None and init_values2 is not None:
        mdt.check.array(init_values1, shape=var2.shape)
        mdt.check.array(init_values2, shape=var1.shape)
        mdt.check.array(data, shape=(len(var1)-1, len(var2)-1))
        if init_values2[0] != init_values1[0]:
            warnings.warn("init_values2[0] ({}) is not the same as"
                          " init_values1[0] ({}). Using init_values1[0]"
                          " as value for the upper left corner."
                          .format(init_values2[0], init_values1[0]),
                          RuntimeWarning)
    
    with open(fname, 'a') as outfile:
        # Block header
        outfile.write("\n\n\n\n")
        if block_number is not None:
            outfile.write("# Block {}\n".format(block_number))
        if data_name is not None:
            outfile.write("# {}".format(data_name))
            if data_unit is not None:
                outfile.write(" in {}\n".format(data_unit))
            else:
                outfile.write("\n")
        if var1_name is not None:
            outfile.write("# First column: {:<10}".format(var1_name))
            if var1_unit is not None:
                outfile.write(" in {}\n".format(var1_unit))
            else:
                outfile.write("\n")
        if var2_name is not None:
            outfile.write("# First row:    {:<10}".format(var2_name))
            if var2_unit is not None:
                outfile.write(" in {}\n".format(var2_unit))
            else:
                outfile.write("\n")
        # Column numbers
        num_cols = len(var2)
        outfile.write("# Column number:\n")
        outfile.write("# {:>16}".format("1"))
        for col_num in range(2, num_cols+2):
            outfile.write(" {:>16}".format(col_num))
        outfile.write("\n")
        # The row after the row with the column numbers contains the
        # values of `var2`.
        if upper_left is None:
            outfile.write("{:>9}\\{:>8}"
                          .format(var1_name[:10], var2_name[:9]))
        else:
            outfile.write("{:>18}".format(upper_left))
        for col_num in range(num_cols):
            outfile.write(" {:16.9e}".format(var2[col_num]))
        outfile.write("\n")
        # If there are any special initial values for the very first
        # value of `var1`, print them to the next row.
        if init_values1 is not None:
            outfile.write("  {:16.9e}".format(var1[0]))
            for col_num in range(num_cols):
                outfile.write(" {:16.9e}".format(init_values1[col_num]))
            outfile.write("\n")
            start_row = 1
        else:
            start_row = 0
        # Print remaining rows. The first column always contains the
        # current value of `var1`. The remaining columns contain the
        # data.
        num_rows = len(var1)
        for row_num in range(start_row, num_rows):
            outfile.write("  {:16.9e}".format(var1[row_num]))
            # If there are any special initial values for the very first
            # value of `var2`, print them to the second column.
            if init_values2 is not None:
                outfile.write(" {:16.9e}".format(init_values2[row_num]))
                start_col = 1
            else:
                start_col = 0
            for col_num in range(start_col, num_cols):
                outfile.write(
                    " {:16.9e}"
                    .format(data[row_num-start_row][col_num-start_col])
                )
            outfile.write("\n")
        outfile.flush()


def load_dtrj(fname, **kwargs):
    """
    Load a discrete trajectory stored as :class:`numpy.ndarray` from a
    binary :file:`.npy` file.
    
    Parameters
    ----------
    fname : str
        Name of the file containing the discrete trajectory.  The
        discrete trajectory must be stored as :class:`numpy.ndarray` in
        the binary :file:`.npy` format.  The array must be of shape
        ``(n, f)``, where ``n`` is the number of compounds and ``f`` is
        the number of frames.  The shape can also be ``(f,)``, in which
        case the array is expanded to shape ``(1, f)``.  The array must
        only contain integers or floats whose fractional part is zero,
        because, the elements of a discrete trajectory are interpreted
        as the indices of the states in which a given compound is at a
        given frame.
    kwargs : dict
        Additional keyword arguments to parse to :func:`numpy.load`.
    
    Returns
    -------
    dtrj : numpy.ndarray
        The discrete trajectory loaded from file.
    
    See Also
    --------
    :func:`numpy.load` :
        Load arrays or pickled objects from :file:`.npy`, :file:`.npz`
        or pickled files
    
    Notes
    -----
    This function simply calls :func:`numpy.load` and checks whether
    the loaded :class:`numpy.ndarray` is a suitable discrete trajectory.
    """
    dtrj = np.load(fname, **kwargs)
    mdt.check.dtrj(dtrj)
    return dtrj
