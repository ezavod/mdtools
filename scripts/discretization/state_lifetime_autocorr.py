#!/usr/bin/env python3


# This file is part of MDTools.
# Copyright (C) 2020  Andreas Thum
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




# Take a look at the notes from 24.01.2021 when writing the
# documentation of this script.




import sys
import os
import warnings
from datetime import datetime
import psutil
import argparse
import numpy as np
from scipy.special import gamma
import mdtools as mdt




# Also used by state_lifetime_autocorr_discrete.py
def dtraj_transition_info(dtraj):
    """
    Returns basic information about the transitions between different
    states in a discretized trajectory.
    
    Parameters
    ----------
    dtraj : array_like
        The discretized trajectory. Array of shape ``(f, n)`` where ``f``
        is the number of frames and ``n`` is the number of compounds.
        The elements of `dtraj` are interpreted as the indices of the
        states in which a given compound is at a given frame.
    
    Returns
    -------
    n_stay : int
        Number of compounds that stay in the same state during the
        entire trajectory.
    always_neg : int
        Number of compounds that are always in a negative state during
        the entire trajectory.
    never_neg : int
        Number of compounds that are never in a negative state during
        the entire trajectory.
    n_frames_neg : int
        Total number of frames with negative states (summed over all
        compounds).
    n_trans : int
        Total number of state transitions.
    pos2pos : int
        Number of Positive -> Positive transitions (transitions from one
        state with a positive state index to another state with a
        positive state index.)
    pos2neg : int
        Number of Positive -> Negative transitions.
    neg2pos : int
        Number of Negative -> Positive transitions.
    neg2neg : int
        Number of Negative -> Negative transitions.
    
    Note
    ----
    Positive states are states with a state index equal(!) to or greater
    than zero. Negative states are states with a state index less than
    zero.
    """
    
    dtraj = np.asarray(dtraj)
    if dtraj.ndim != 2:
        raise ValueError("dtraj must have two dimensions")
    
    n_stay = np.count_nonzero(np.all(dtraj==dtraj[0], axis=0))
    always_neg = np.count_nonzero(np.all(dtraj<0, axis=0))
    never_neg = np.count_nonzero(np.all(dtraj>=0, axis=0))
    n_frames_neg = np.count_nonzero(dtraj<0)
    
    n_compounds = dtraj.shape[1]
    transitions = (np.diff(dtraj, axis=0) != 0)
    trans_init = np.vstack([transitions, np.zeros(n_compounds, dtype=bool)])
    trans_final = np.insert(transitions, 0, np.zeros(n_compounds), axis=0)
    n_trans = np.count_nonzero(transitions)
    if np.count_nonzero(trans_init) != n_trans:
        raise ValueError("The number of transitions in trans_init is not"
                         " the same as in transitions. This should not"
                         " have happened")
    if np.count_nonzero(trans_final) != n_trans:
        raise ValueError("The number of transitions in trans_final is"
                         " not the same as in transitions. This should"
                         " not have happened")
    pos2pos = np.count_nonzero((dtraj[trans_init] >= 0) &
                               (dtraj[trans_final] >= 0))
    pos2neg = np.count_nonzero((dtraj[trans_init] >= 0) &
                               (dtraj[trans_final] < 0))
    neg2pos = np.count_nonzero((dtraj[trans_init] < 0) &
                               (dtraj[trans_final] >= 0))
    neg2neg = np.count_nonzero((dtraj[trans_init] < 0) &
                               (dtraj[trans_final] < 0))
    if pos2pos + pos2neg + neg2pos + neg2neg != n_trans:
        raise ValueError("The sum of Positive <-> Negative transitions"
                         " ({}) is not equal to the total number of"
                         " transitions ({}). This should not have"
                         " happened"
                         .format(pos2pos+pos2neg+neg2pos+neg2neg,
                                 n_trans))
    
    return (n_stay, always_neg, never_neg, n_frames_neg,
            n_trans, pos2pos, pos2neg, neg2pos, neg2neg)




def autocorr_dtraj(dtraj, restart=1, cut=False, cut_and_merge=False):
    """
    Calculate the autocorrelation function of a discretized trajectory,
    with the speciality that the autocovariance is set to one, if the
    state :math:`S` after a lag time :math:`\tau` is the same as at time
    :math:`t_0`. Otherwise, the autocovariance is zero. That means the
    calculated quantity is
    
    .. math::
        C(\tau) = \langle \frac{S(t_0) S(t_0+\tau)}{S(t_0) S(t_0)} \rangle
    
    with :math:`S(t) \cdot S(t')` being the Kronecker delta:
    
    .. math::
        S(t) S(t') = \delta_{S(t),S(t')}
    
    The brackets :math:`\langle ... \rangle` denote averaging over all
    states :math:`S` in the trajectory and over all possible starting
    times :math:`t_0`. You can interprete :math:`C(\tau)` as the
    percentage of states that have not changed or have come back to the
    initial state after a lag time :math:`\tau`.
    
    Between this function and :func:`state_decay` from state_decay.py
    exists a subtle but distinct difference. Compounds that return into
    their initial state after being in at least one other state,
    increase the autocorrelation function, since
    :math:`S(t_0) S(t_0+\tau)` will be one again. However, in
    :func:`state_decay` :math:`S(t_0) S(t_0+\tau)` will stay zero once
    it has become zero. That means :func:`state_decay` is insensitive
    of compounds that return into their initial states.
    
    Parameters
    ----------
    dtraj : array_like
        The discretized trajectory. Array of shape ``(f, n)`` where ``f``
        is the number of frames and ``n`` is the number of compounds.
        The elements of `dtraj` are interpreted as the indices of the
        states in which a given compound is at a given frame.
    restart : int, optional
        Number of frames between restarting points :math:`t_0`.
    cut : int, optional
        If ``True``, states with negative indices are effectively cut
        out of the trajectory. The cutting edges are not merged so that
        you effectively get multiple smaller trajectories. This means,
        negative states are ignored completely. Even transitions from
        positive to negative states will not be counted and hence will
        not influence the autocorrelation function. Practically seen,
        you discard all restarting and end points where the state index
        is negative.
    cut_and_merge : int, optional
        If ``True``, states with negative indices are effectively cut
        out of the trajectory. The cutting edges are merged to one new
        trajectory. This means, transitions from positive to negative
        states will still be counted and decrease the autocorrelation
        function. But otherwise, negative states are completely ignored
        and do not influence the autocorrelation function. Practically
        seen, you discard all restarting points where the state index is
        negative. In short, the difference between `cut` and
        `cut_and_merge` is that a transition from a positive to a
        negative state is not counted when using `cut`, whereas it is
        counted when using `cut_and_merge`. In both cases all
        transitions starting from negative states are ignored, as well
        as compounds that stay in the same negative state. `cut` and
        `cut_and_merge` are mutually exclusive.
    
    Returns
    -------
    autocorr : numpy.ndarray
        Array of shape ``f`` containing the values of :math:`C(\tau)`
        for each lag time :math:`\tau`.
    """
    
    dtraj = np.asarray(dtraj)
    if dtraj.ndim != 2:
        raise ValueError("dtraj must have two dimensions")
    if np.any(np.modf(dtraj)[0] != 0):
        warnings.warn("At least one element of the discrete trajectory"
                      " is not an integer", RuntimeWarning)
    
    if cut and cut_and_merge:
        raise ValueError("cut and cut_and_merge are mutually exclusive")
    if cut or cut_and_merge:
        valid = np.any(dtraj>=0, axis=0)
        if np.count_nonzero(valid)/len(valid) < 0.9:
            # Trade-off between reduction of computations and memory
            # consumption
            dtraj = np.asarray(dtraj[:,valid], order='C')
    
    n_frames = dtraj.shape[0]
    n_compounds = dtraj.shape[1]
    autocorr = np.zeros(n_frames, dtype=np.float32)
    autocov = np.zeros(n_compounds, dtype=bool)
    
    if cut or cut_and_merge:
        valid = np.zeros(n_compounds, dtype=bool)
        norm = np.zeros(n_frames, dtype=np.uint32)
    if cut:
        valid2 = np.zeros(n_compounds, dtype=bool)
        valid3 = np.zeros(n_compounds, dtype=bool)
    
    
    proc = psutil.Process(os.getpid())
    timer = datetime.now()
    for t0 in range(0, n_frames-1, restart):
        if t0 % 10**(len(str(t0))-1) == 0 or t0 == n_frames-2:
            print("  Restart {:12d} of {:12d}"
                  .format(t0, n_frames-2),
                  flush=True)
            print("    Elapsed time:             {}"
                  .format(datetime.now()-timer),
                  flush=True)
            print("    Current memory usage: {:18.2f} MiB"
                  .format(proc.memory_info().rss/2**20),
                  flush=True)
            timer = datetime.now()
        
        if cut:
            np.greater_equal(dtraj[t0], 0, out=valid)
            for lag in range(1, n_frames-t0):
                np.greater_equal(dtraj[t0+lag], 0, out=valid2)
                np.equal(valid, valid2, out=valid3)
                if not np.any(valid3):
                    break
                np.equal(dtraj[t0], dtraj[t0+lag], out=autocov)
                autocorr[lag] += np.count_nonzero(autocov[valid3])
                norm[lag] += np.count_nonzero(valid3)
        #if cut:
            #np.greater_equal(dtraj[t0], 0, out=valid)
            #for lag in range(1, n_frames-t0):
                #np.greater_equal(dtraj[t0+lag], 0, out=valid2)
                #valid &= valid2
                #if not np.any(valid):
                    #break
                #np.equal(dtraj[t0], dtraj[t0+lag], out=autocov)
                #autocorr[lag] += np.count_nonzero(autocov[valid])
                #norm[lag] += np.count_nonzero(valid)
        elif cut_and_merge:
            np.greater_equal(dtraj[t0], 0, out=valid)
            n_valid = np.count_nonzero(valid)
            if n_valid == 0:
                continue
            norm[1:n_frames-t0] += n_valid
            for lag in range(1, n_frames-t0):
                np.equal(dtraj[t0], dtraj[t0+lag], out=autocov)
                autocorr[lag] += np.count_nonzero(autocov[valid])
        else:  # not cut and not cut_and_merge
            for lag in range(1, n_frames-t0):
                np.equal(dtraj[t0], dtraj[t0+lag], out=autocov)
                autocorr[lag] += np.count_nonzero(autocov)
    
    del dtraj, autocov
    
    
    if cut or cut_and_merge:
        if norm[0] != 0:
            raise ValueError("The first element of norm is not zero."
                             " This should not have happened")
        norm[0] = 1
        autocorr /= norm
    else:  # not cut and not cut_and_merge
        n_restarts = np.arange(n_frames, 0, -1, dtype=np.float32)
        n_restarts /= restart
        np.ceil(n_restarts, out=n_restarts)
        autocorr /= n_restarts
        autocorr /= n_compounds
    
    if autocorr[0] != 0:
        raise ValueError("The first element of autocorr is not zero."
                         " This should not have happened")
    autocorr[0] = 1
    if np.any(autocorr > 1):
        raise ValueError("At least one element of autocorr is greater"
                         " than one. This should not have happened")
    if np.any(autocorr < 0):
        raise ValueError("At least one element of autocorr is less than"
                         " zero. This should not have happened")
    
    return autocorr








if __name__ == '__main__':
    
    timer_tot = datetime.now()
    proc = psutil.Process(os.getpid())
    
    
    parser = argparse.ArgumentParser(
                 description=(
                     "Read a discretized trajectory, as e.g. generated"
                     " by discrete_coord.py or discrete_hex.py, and"
                     " calculate the average lifetime of the discrete"
                     " states, i.e. the average time for how long a"
                     " specific state exists before it changes to"
                     " another state. This is done by computing the"
                     " autocorrelation function of the discrete"
                     " trajectory, with the speciality that the"
                     " autocovariance is set to one if the state after a"
                     " lag time tau is the same as at time t0."
                     " Otherwise, the autocovariance is set to zero."
                     " Finally, the autocorrelation function (normalized"
                     " autocovariance) is fitted by a stretched"
                     " exponential function, whose integral from zero to"
                     " infinity is the averave lifetime of all states in"
                     " the discretized trajectory. Between this script"
                     " state_decay.py exists a subtle but distinct"
                     " difference. Compounds that return into their"
                     " initial state after being in at least one other"
                     " state will increase the autocorrelation function"
                     " again. However, in state_decay.py compounds that"
                     " return into their initial states will not have"
                     " any influence."
                     )
    )
    group = parser.add_mutually_exclusive_group()
    
    parser.add_argument(
        '-f',
        dest='TRJFILE',
        type=str,
        required=True,
        help="File containing the discretized trajectory stored as"
             " numpy.ndarray in .npy format. The array must be of shape"
             " (n, f) where n is the number of compounds and f is the"
             " number of frames. The elements of the array are"
             " interpreted as the indices of the states in which a given"
             " compound is at a given frame."
    )
    parser.add_argument(
        '-o',
        dest='OUTFILE',
        type=str,
        required=True,
        help="Output filename."
    )
    
    parser.add_argument(
        '-b',
        dest='BEGIN',
        type=int,
        required=False,
        default=0,
        help="First frame to read. Frame numbering starts at zero."
             " Default: 0"
    )
    parser.add_argument(
        '-e',
        dest='END',
        type=int,
        required=False,
        default=-1,
        help="Last frame to read (exclusive, i.e. the last frame read is"
             " actually END-1). Default: -1 (means read the very last"
             " frame of the trajectory)"
    )
    parser.add_argument(
        '--every',
        dest='EVERY',
        type=int,
        required=False,
        default=1,
        help="Read every n-th frame. Default: 1"
    )
    parser.add_argument(
        '--nblocks',
        dest='NBLOCKS',
        type=int,
        required=False,
        default=1,
        help="Number of blocks for block averaging. The trajectory will"
             " be split in NBLOCKS equally sized blocks, which will be"
             " analyzed independently, like if they were different"
             " trajectories. Finally, the average and standard deviation"
             " over all blocks will be calculated. Default: 1"
    )
    parser.add_argument(
        '--restart',
        dest='RESTART',
        type=int,
        default=100,
        help="Number of frames between restarting points for calculating"
             " the autocorrelation function. This must be an integer"
             " multiple of --every. Ideally, RESTART should be larger"
             " than the longest lifetime to ensure independence of each"
             " restart window. Default: 100"
    )
    
    group.add_argument(
        '--cut',
        dest='CUT',
        required=False,
        default=False,
        action='store_true',
        help="If set, states with negative indices are effectively cut"
             " out of the trajectory. The cutting edges are not merged"
             " so that you effectively get multiple smaller trajectories."
             " This means, negative states are ignored completely. Even"
             " transitions from positive to negative states will not be"
             " counted and hence will not influence the autocorrelation"
             " function. Practically seen, you discard all restarting"
             " and end points where the state index is negative."
    )
    group.add_argument(
        '--cut-and-merge',
        dest='CUT_AND_MERGE',
        required=False,
        default=False,
        action='store_true',
        help="If set, states with negative indices are effectively cut"
             " out of the trajectory. The cutting edges are merged to"
             " one new trajectory. This means, transitions from positive"
             " to negative states will still be counted and decrease the"
             " autocorrelation function. But otherwise, negative states"
             " are completely ignored and do not influence the"
             " autocorrelation function. Practically seen, you discard"
             " all restarting points where the state index is negative."
             " In short, the difference between --cut and"
             " --cut-and-merge is that a transition from a positive to a"
             " negative state is not counted when using --cut, whereas"
             " it is counted when using --cut-and-merge. In both cases"
             " all transitions starting from negative states are"
             " ignored, as well as compounds that stay in the same"
             " negative state. --cut and --cut-and-merge are mutually"
             " exclusive."
    )
    
    parser.add_argument(
        '--end-fit',
        dest='ENDFIT',
        type=float,
        required=False,
        default=None,
        help="End time for fitting the autocorrelation function (in"
             " trajectory steps). Inclusive, i.e. the time given here is"
             " still included in the fit. Default: End at 90%% of the"
             " trajectory."
    )
    parser.add_argument(
        '--stop-fit',
        dest='STOPFIT',
        type=float,
        required=False,
        default=0.01,
        help="Stop fitting the autocorrelation function as soon as it"
             " falls below this value. The fitting is stopped by"
             " whatever happens earlier: --end-fit or --stop-fit."
             " Default: 0.01"
    )
    
    
    args = parser.parse_args()
    print(mdt.rti.run_time_info_str())
    
    
    
    
    print("\n\n\n", flush=True)
    print("Reading input", flush=True)
    timer = datetime.now()
    
    dtrajs = np.load(args.TRJFILE)
    if dtrajs.ndim == 1:
        dtrajs = np.expand_dims(dtrajs, axis=0)
    elif dtrajs.ndim > 2:
        raise ValueError("The discrete trajectory must have one or two"
                         " dimensions")
    dtrajs = np.asarray(dtrajs.T, order='C')
    n_frames = dtrajs.shape[0]
    n_compounds = dtrajs.shape[1]
    print("  Number of frames:    {:>9d}".format(n_frames), flush=True)
    print("  Number of compounds: {:>9d}"
          .format(n_compounds),
          flush=True)
    if np.any(np.modf(dtrajs)[0] != 0):
        warnings.warn("At least one element of the discrete trajectory"
                      " is not an integer", RuntimeWarning)
    
    BEGIN, END, EVERY, n_frames = mdt.check.frame_slicing(
                                      start=args.BEGIN,
                                      stop=args.END,
                                      step=args.EVERY,
                                      n_frames_tot=n_frames)
    NBLOCKS, blocksize = mdt.check.block_averaging(n_blocks=args.NBLOCKS,
                                                   n_frames=n_frames)
    RESTART, effective_restart = mdt.check.restarts(
                                     restart_every_nth_frame=args.RESTART,
                                     read_every_nth_frame=EVERY,
                                     n_frames=blocksize)
    dtrajs = dtrajs[BEGIN:END:EVERY]
    
    trans_info = dtraj_transition_info(dtraj=dtrajs[:NBLOCKS*blocksize])
    
    print("Elapsed time:         {}"
          .format(datetime.now()-timer),
          flush=True)
    print("Current memory usage: {:.2f} MiB"
          .format(proc.memory_info().rss/2**20),
          flush=True)
    
    
    
    
    print("\n\n\n", flush=True)
    print("Calculating autocorrelation function", flush=True)
    timer = datetime.now()
    timer_block = datetime.now()
    
    autocorr = [None,] * NBLOCKS
    for block in range(NBLOCKS):
        if block % 10**(len(str(block))-1) == 0 or block == NBLOCKS-1:
            print(flush=True)
            print("  Block   {:12d} of {:12d}"
                  .format(block, NBLOCKS-1),
                  flush=True)
            print("    Elapsed time:             {}"
                  .format(datetime.now()-timer_block),
                  flush=True)
            print("    Current memory usage: {:18.2f} MiB"
                  .format(proc.memory_info().rss/2**20),
                  flush=True)
            timer_block = datetime.now()
        autocorr[block] = autocorr_dtraj(
                              dtraj=dtrajs[block*blocksize:(block+1)*blocksize],
                              restart=effective_restart,
                              cut=args.CUT,
                              cut_and_merge=args.CUT_AND_MERGE)
    del dtrajs
    
    autocorr = np.asarray(autocorr)
    if NBLOCKS > 1:
        autocorr, autocorr_sd = mdt.stats.block_average(autocorr)
    else:
        autocorr = np.squeeze(autocorr)
        autocorr_sd = None
    
    print("Elapsed time:         {}"
          .format(datetime.now()-timer),
          flush=True)
    print("Current memory usage: {:.2f} MiB"
          .format(proc.memory_info().rss/2**20),
          flush=True)
    
    
    
    
    print("\n\n\n", flush=True)
    print("Fitting autocorrelation function", flush=True)
    timer = datetime.now()
    
    lag_times = np.arange(blocksize, dtype=np.uint32)
    
    if args.ENDFIT is None:
        endfit = int(0.9 * len(lag_times))
    else:
        _, endfit = mdt.nph.find_nearest(lag_times,
                                         args.ENDFIT,
                                         return_index=True)
    endfit += 1  # To make args.ENDFIT inclusive
    
    stopfit = np.argmax(autocorr < args.STOPFIT)
    if stopfit == 0 and autocorr[stopfit] >= args.STOPFIT:
        stopfit = len(autocorr)
    elif stopfit < 2:
        stopfit = 2
    
    fit_start = 0                    # inclusive
    fit_stop = min(endfit, stopfit)  # exclusive
    valid = np.isfinite(autocorr) & (autocorr > 0) & (autocorr <= 1)
    valid[:fit_start] = False
    valid[fit_stop:] = False
    
    if autocorr_sd is None:
        popt, perr = mdt.func.fit_kww(xdata=lag_times[valid],
                                      ydata=autocorr[valid])
    else:
        popt, perr = mdt.func.fit_kww(xdata=lag_times[valid],
                                      ydata=autocorr[valid],
                                      ysd=autocorr_sd[valid])
    tau_mean = popt[0]/popt[1] * gamma(1/popt[1])
    fit = mdt.func.kww(t=lag_times, tau=popt[0], beta=popt[1])
    fit[~valid] = np.nan
    del valid
    
    print("Elapsed time:         {}"
          .format(datetime.now()-timer),
          flush=True)
    print("Current memory usage: {:.2f} MiB"
          .format(proc.memory_info().rss/2**20),
          flush=True)
    
    
    
    
    print("\n\n\n", flush=True)
    print("Creating output", flush=True)
    timer = datetime.now()
    
    header = (
        "Average lifetime of all discrete states in the discretized\n"
        "trajectory\n"
        "\n"
        "\n"
        "Number of frames (per compound):                         {:>12d}\n"
        "Number of compounds:                                     {:>12d}\n"
        "Number of compounds that never leave their state:        {:>12d}\n"
        "Number of compounds that are always in a negative state: {:>12d}\n"
        "Number of compounds that are never  in a negative state: {:>12d}\n"
        "Total number of frames with negative states:             {:>12d}\n"
        "\n"
        "Total number of state transitions:          {:>12d}\n"
        "Number of Positive -> Positive transitions: {:>12d}  ({:>8.4f} %)\n"
        "Number of Positive -> Negative transitions: {:>12d}  ({:>8.4f} %)\n"
        "Number of Negative -> Positive transitions: {:>12d}  ({:>8.4f} %)\n"
        "Number of Negative -> Negative transitions: {:>12d}  ({:>8.4f} %)\n"
        "Positive states are states with a state index >= 0\n"
        "Negative states are states with a state index <  0\n"
        "\n"
        "\n"
        "The average lifetime <tau> is estimated from the integral of a\n"
        "stretched exponential fit of the autocorrelation function of\n"
        "the discrete trajectory. The autocorrelation of the discrete\n"
        "trajectory is calculated with the speciality that the\n"
        "autocovariance is set to one if the state S after a lag time\n"
        "t is the same as at time t0. Otherwise, the autocovariance is\n"
        "set to zero.\n"
        "\n"
        "Autocovariance:\n"
        "  S(t0)*S(t0+t) = 1, if S(t0)=S(t0+t)\n"
        "  S(t0)*S(t0+t) = 0, otherwise\n"
        "\n"
        "Autocorrelation function:\n"
        "  C(t) = < S(t0)*S(t0+t) / S(t0)*S(t0) >\n"
        "  <...> = Average over all states S in the trajectory and\n"
        "          over all possible starting times t0\n"
        "  You can interprete C(t) as the percentage of states that\n"
        "  have not changed or have come back to the initial state\n"
        "  after a lag time t\n"
        "\n"
        "The autocorrelation is fitted using a stretched exponential\n"
        "function, also known as Kohlrausch-Williams-Watts (KWW)\n"
        "function:\n"
        "  f(t) = exp[-(t/tau)^beta]\n"
        "  beta is constrained to the intervall [0, 1]\n"
        "  tau must be positive\n"
        "\n"
        "The average lifetime <tau> is calculated as the integral of\n"
        "the KWW function from zero to infinity:\n"
        "  <tau> = integral_0^infty exp[-(t/tau)^beta] dt\n"
        "        = tau/beta * Gamma(1/beta)\n"
        "  Gamma(x) = Gamma function\n"
        "  If beta=1, <tau>=tau\n"
        "\n"
        "\n"
        .format(n_frames, n_compounds,
                trans_info[0], trans_info[1],
                trans_info[2], trans_info[3],
                trans_info[4],
                trans_info[5], 100*trans_info[5]/trans_info[4],
                trans_info[6], 100*trans_info[6]/trans_info[4],
                trans_info[7], 100*trans_info[7]/trans_info[4],
                trans_info[8], 100*trans_info[8]/trans_info[4]
        )
    )
    if NBLOCKS == 1:
        header += (
            "The columns contain:\n"
            "  1 Lag time t (in trajectory steps)\n"
            "  2 Autocorrelation function\n"
            "  3 Fit of the autocorrelation function\n"
            "\n"
            "Column number:\n"
            "{:>14d} {:>16d} {:>16d}\n"
            "\n"
            "Fit:\n"
            "Fit start (steps):               {:>15.9e}\n"
            "Fit stop  (steps):               {:>15.9e}\n"
            "Average lifetime <tau> (steps):  {:>15.9e}\n"
            "Relaxation time tau (steps):     {:>15.9e}\n"
            "Std. dev. of tau (steps):        {:>15.9e}\n"
            "Stretching exponent beta:        {:>15.9e}\n"
            "Standard deviation of beta:      {:>15.9e}\n"
            .format(1, 2, 3,
                    fit_start, fit_stop,
                    tau_mean, popt[0], perr[0], popt[1], perr[1])
        )
        data = np.column_stack([lag_times, autocorr, fit])
    else:
        header += (
            "The columns contain:\n"
            "  1 Lag time t (in trajectory steps)\n"
            "  2 Autocorrelation function\n"
            "  3 Standard deviation of the autocorrelation function\n"
            "  4 Fit of the autocorrelation function\n"
            "\n"
            "Column number:\n"
            "{:>14d} {:>16d} {:>16d} {:>16d}\n"
            "\n"
            "Fit:\n"
            "Fit start (steps):               {:>32.9e}\n"
            "Fit stop  (steps):               {:>32.9e}\n"
            "Average lifetime <tau> (steps):  {:>32.9e}\n"
            "Relaxation time tau (steps):     {:>32.9e}\n"
            "Std. dev. of tau (steps):        {:>32.9e}\n"
            "Stretching exponent beta:        {:>32.9e}\n"
            "Standard deviation of beta:      {:>32.9e}\n"
            .format(1, 2, 3, 4,
                    fit_start, fit_stop,
                    tau_mean, popt[0], perr[0], popt[1], perr[1])
        )
        data = np.column_stack([lag_times, autocorr, autocorr_sd, fit])
    
    mdt.fh.savetxt(fname=args.OUTFILE, data=data, header=header)
    
    print("  Created {}".format(args.OUTFILE), flush=True)
    print("Elapsed time:         {}"
          .format(datetime.now()-timer),
          flush=True)
    print("Current memory usage: {:.2f} MiB"
          .format(proc.memory_info().rss/2**20),
          flush=True)
    
    
    
    
    print("\n\n\n{} done".format(os.path.basename(sys.argv[0])))
    print("Elapsed time:         {}"
          .format(datetime.now()-timer_tot),
          flush=True)
    print("Current memory usage: {:.2f} MiB"
          .format(proc.memory_info().rss/2**20),
          flush=True)
