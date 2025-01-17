#!/usr/bin/env python3

# This file is part of MDTools.
# Copyright (C) 2021  The MDTools Development Team and all contributors
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
Calculate contact histograms based on contact matrices.

.. deprecated:: 0.0.0.dev0
    Use :mod:`contact_hist` instead.
"""


__author__ = "Andreas Thum"


# Standard libraries
import sys
import os
import warnings
import argparse
from datetime import datetime, timedelta
# Third party libraries
import psutil
import numpy as np
# Local application/library specific imports
import mdtools as mdt


def contact_hist(
        ref, sel, cutoff, expected_max_contacts=16, debug=False):
    """
    Calculate the number of contacts between two MDAnalysis
    :class:`AtomGroups <AtomGroups<MDAnalysis.core.groups.AtomGroup>`.
    
    Contacts are counted by looping over all atoms of the reference
    group (`ref`) and searching for atoms of the selection group (`sel`)
    that are within the given cutoff.
    
    Contacts are binned into histograms according to how many different
    selection atoms/residues have contact with a given reference
    atom/residue and according to how many contacts exist between a
    given selection-atom/residue reference-atom/residue pair.  The
    histograms are not normalized, that means the product sum over all
    elements of a histogram times their respective index gives the total
    number of contacts.
    
    Parameters
    ----------
    ref : MDAnalysis.core.groups.AtomGroup instance
        MDAnalysis :class:`~MDAnalysis.core.groups.AtomGroup` or
        :class:`~MDAnalysis.core.groups.UpdatingAtomGroup` serving as
        reference group.
    sel : MDAnalysis.core.groups.AtomGroup instance
        MDAnalysis :class:`~MDAnalysis.core.groups.AtomGroup` or
        :class:`~MDAnalysis.core.groups.UpdatingAtomGroup` serving as
        selection group.
    cutoff : scalar
        Cutoff that a reference and selection atom must not exceed to be
        considered as connected.
    expected_max_contacts : int, optional
        Expected maximum number of contacts a single reference atom can
        establish to selection atoms.  This determines the initial
        length of the histogram array.  If it is too small, it is likely
        that it has to be extended, which is computaionally inefficient.
        If it is unnecessarily large, you waste memory and also invoke
        unnecessary computations on zeros.  If you parse a non-positive
        value, `expected_max_contacts` is set to its default value.
    debug : bool, optional
       If ``True``, check the returned histograms for inconsistencies.
    
    Returns
    -------
    refatm_selatm : numpy.ndarray
        Histogram of contacts between *reference and selection atoms*.
    refatm_diff_selres : numpy.ndarray
        Histogram of contacts between *reference atoms* and *different
        selection residues*, multiple contacts with the same selection
        residue being discounted.
    refatm_same_selres : numpy.ndarray
        Histogram of contacts between *reference atoms* and the *same
        selection residue*.  Different selection residues that are
        connected to the same reference atom via the same number of
        "bonds" (contacts) are discounted.
    refres_diff_selatm : numpy.ndarray
        Histogram of contacts between *reference residues* and
        *different selection atoms*, multiple contacts with the same
        selection atom being discounted.
    refres_same_selatm : numpy.ndarray
        Histogram of contacts between *reference residues* and the *same
        selection atom*.  Different selection atoms that are connected
        to the same reference residue via the same number of "bonds"
        (contacts) are discounted.
    refres_selatm_tot : numpy.ndarray
        Histogram of contacts between *reference residues* and
        *selection atoms*, multiple contacts with the same selection
        atom being counted.
    refres_diff_selres : numpy.ndarray
        Histogram of contacts between *reference residues* and
        *different selection residues*, multiple contacts with the same
        selection residue being discounted.
    refres_same_selres : numpy.ndarray
        Histogram of contacts between *reference residues* and the *same
        selection residue*.  Different selection residues that are
        connected to the same reference residue via the same number of
        "bonds" (contacts) are discounted.
    refatm_selres_pair : numpy.ndarray
        Histogram of "bonds" (contacts) between refatm-selres pairs.  A
        refatm-selres pair is defined as a reference atom and a
        selection residue that are connected with each other via at
        least one "bond".
    refres_selatm_pair : numpy.ndarray
        Histogram of "bonds" (contacts) between refres-selatm pairs.
    refres_selres_pair : numpy.ndarray
        Histogram of "bonds" (contacts) between refres-selres pairs.
    
    See Also
    --------
    :func:`contact_hist_at_pos_change.contact_hist_atm` :
        Only takes into account reference atoms
    :func:`contact_hist_at_pos_change.contact_hist_res`
        Only takes into account reference residues
    
    Notes
    -----
    Probably, in most cases you will only need `refatm_selatm` and
    `refatm_diff_selres` and maybe `refatm_same_selres` and
    `refatm_selres_pair` to quantify multidentate coordinations.
    However, when calculating these histograms, it is not too much
    effort to calculate the other histograms, too, because then the
    computationally expensive task of finding the relevant selection
    atoms in the vicinity of the reference atoms is already done.
    
    Note that the term 'residue' is synonymous with the term 'atom' if
    the residue consists of only one atom (or if only one atom of the
    residue is contained in the reference or selection
    :class:`MDAnalysis.core.groups.AtomGroup`)
    
    Reference-atom selection-atom histograms:
    
        * `refatm_selatm`: Histogram of contacts between *reference and
          selection atoms*.
            
            - The first element is the number of reference atoms having
              no contact with any selection atom, the second element is
              the number of reference atoms having contact with exactly
              one selection atom, the third element is the number of
              reference atoms having contact with exactly two
              *different* selection atoms, and so on.
            - `refatm_selatm` = `refatm_diff_selatm` =
              `refatm_selatm_tot` = `refatm_selres_tot`.
        
        * `refatm_diff_selatm`: Histogram of contacts between *reference
          atoms* and *different selection atoms*, multiple contacts with
          the same selection atom being discounted.
            
            - **Not returned**, only listed for completness.
            - Same as `refatm_selatm`, because an *atom* can either have
              one or no contact with another atom, but not multiple
              contacts, because contacts are defined by a simple
              distance criterium.
        
        * `refatm_same_selatm`: Histogram of contacts between *reference
          atoms* and the *same selection atom*.  Different selection
          atoms that are connected to the same reference atom via the
          same number of "bonds" (contacts) are discounted.
            
            - **Not returned**, only listed for completness.
            - This array is simply ``[x, Nrefatm-x]`` with ``x`` being
              the number of reference atoms not in contact with any
              selection atom and ``Nrefatm`` being the total number of
              reference atoms.  This holds true, because an *atom* can
              either have one or no contact with another atom (see
              `refatm_diff_selatm`).
        
        * `refatm_selatm_tot`: Histogram of contacts between *reference
          and selection atoms*, multiple contacts with the same
          selection atom being counted.
            
            - **Not returned**, only listed for completness.
            - Same as `refatm_selatm`, because an *atom* can either have
              one or no contact with another atom (see
              `refatm_diff_selatm`).
    
    Reference-atom selection-residue histograms:
    
        * `refatm_diff_selres`: Histogram of contacts between *reference
          atoms* and *different selection residues*, multiple contacts
          to the same selection residue being discounted.
            
            - The first element is the number of reference atoms having
              no contact with any selection residue, the second element
              is the number of reference atoms having contact with
              exactly one selection residue, the third element is the
              number of reference atoms having contact with exactly two
              *different* selection residues, and so on.
        
        * `refatm_same_selres`: Histogram of contacts between *reference
          atoms* and the *same selection residue*.  Different selection
          residues that are connected to the same reference atom via the
          same number of "bonds" (contacts) are discounted.
            
            - For instance, if a reference atom is connected to two
              different selection residues via one "bond", respectively,
              only the first selection residue is counted.  However, if
              the reference atom is connected to the first selection
              residue via one "bond" and to the second selection residue
              via two "bonds", both selection residues are counted.
            - The first element is the number of reference atoms having
              no contact with any selection residue, the second element
              is the number of reference atoms having *at least* one
              connection to a selection residue via exactly one "bond",
              the third element is the number of reference atoms having
              at least one connection to a selection residue via exactly
              two "bonds", and so on.
            - Note that the sum of all histogram elements might exceed
              the number of reference atoms, because a single reference
              atom can be connected to different selection residues with
              different numbers of "bonds".  However, each histogram
              element on its own cannot exceed the number of reference
              atoms, because different selection residues that are
              connected to the same reference atom via the same number
              of "bonds" are discounted.
            - Complementary to `refatm_selres_pair`.
        
        * `refatm_selres_tot`: Histogram of contacts between *reference
          atoms* and *selection residues*, multiple contacts with the
          same selection residue being counted.
            
            - **Not returned**, only listed for completness.
            - Same as `refatm_selatm`, because the number of reference
              atoms having `N` contacts with selection *residues* is the
              same as the number of reference atoms having `N` contacts
              with selection *atoms* (`refatm_selatm_tot`).  And because
              an *atom* can either have one or no contact with another
              atom (see `refatm_diff_selatm`), `refatm_selatm_tot` (and
              therefore `refatm_selres_tot`) is the same as
              `refatm_selatm`.
    
    Reference-residue selection-atom histograms:
    
        * `refres_diff_selatm`: Histogram of contacts between *reference
          residues* and *different selection atoms*, multiple contacts
          with the same selection atom being discounted.
            
            - The first element is the number of reference residues
              having no contact with any selection atom, the second
              element is the number of reference residues having contact
              with exactly one selection atom, the third element is the
              number of reference residues having contact with exactly
              two *different* selection atoms, and so on.
        
        * `refres_same_selatm`: Histogram of contacts between *reference
          residues* and the *same selection atom*.  Different selection
          atoms that are connected to the same reference residue via the
          same number of "bonds" (contacts) are discounted.
            
            - For instance, if a reference residue is connected to two
              different selection atoms via one "bond", respectively,
              only the first selection atom is counted.  However, if the
              reference residue is connected to the first selection atom
              via one "bond" and to the second selection atom via two
              "bonds", both selection atoms are counted.
            - The first element is the number of reference residues
              having no contact with any selection atom, the second
              element is the number of reference residues having *at
              least* one connection to a selection atom via exactly one
              "bond", the third element is the number of reference
              residues having at least one connection to a selection
              atom via exactly two "bonds", and so on.
            - Note that the sum of all histogram elements might exceed
              the number of reference residues, because a single
              reference residue can be connected to different selection
              atoms with different numbers of "bonds".  However, each
              histogram element on its own cannot exceed the number of
              reference residues, because different selection atoms that
              are connected to the same reference residue via the same
              number of "bonds" are discounted.
            - Complementary to `refres_selatm_pair`.
        
        * `refres_selatm_tot`: Histogram of contacts between *reference
          residues* and *selection atoms*, multiple contacts with the
          same selection atom being counted.
            
            - The first element is the number of reference residues
              having no contact with any selection atom, the second
              element is the number of reference residues having exactly
              one contact with selection atoms, the third element is the
              number of reference residues having exactly two contacts
              with selection atoms, and so on.
    
    Reference-residue selection-residue histograms:
    
        * `refres_diff_selres`: Histogram of contacts between *reference
          residues* and *different selection residues*, multiple
          contacts with the same selection residue being discounted.
            
            - The first element is the number of reference residues
              having no contact with any selection residue, the second
              element is the number of reference residues having contact
              with exactly one selection residue, the third element is
              the number of reference residues having contact with
              exactly two *different* selection residues, and so on.
        
        * `refres_same_selres`: Histogram of contacts between *reference
          residues* and the *same selection residue*.  Different
          selection residues that are connected to the same reference
          residue via the same number of "bonds" (contacts) are
          discounted.
            
            - For instance, if a reference residue is connected to two
              different selection residues via one "bond", respectively,
              only the first selection residue is counted.  However, if
              the reference residue is connected to the first selection
              residue via one "bond" and to the second selection resdiue
              via two "bonds", both selection residues are counted.
            - The first element is the number of reference residues
              having no contact with any selection residue, the second
              element is the number of reference residues having *at
              least* one connection to a selection residue via exactly
              one "bond", the third element is the number of reference
              residues having at least one connection to a selection
              residue via exactly two "bonds", and so on.
            - Note that the sum of all histogram elements might exceed
              the number of reference residues, because a single
              reference residues can be connected to different selection
              residues with different numbers of "bonds".  However, each
              histogram element on its own cannot exceed the number of
              reference residues, because different selection residues
              that are connected to the same reference residue via the
              same number of "bonds" are discounted.
            - Complementary to `refres_selres_pair`.
        
        * `refres_selres_tot`: Histogram of contacts between *reference
          residues* and *selection residues*, multiple contacts with the
          same selection residue being counted.
            
            - **Not returned**, only listed for completness.
            - Same as `refres_selatm_tot`, because the number of
              reference residues having `N` contacts with selection
              *residues* is the same as the number of reference
              residues having `N` contacts with selection *atoms*.
    
    Histograms counting how many "bonds" (contacts) exist between
    connected reference-atom/residue selection-atom/residue pairs:
    
        * `refatm_selatm_pair`: Histogram of "bonds" (contacts) between
          refatm-selatm pairs.  A refatm-selatm pair is defined as a
          reference atom and a selection atom that are connected with
          each other via at least one "bond".
            
            - **Not returned**, only listed for completness.
            - This array is simply ``[0, y]`` with ``y`` being the
              number of refatm-selatm pairs, because an *atom* can
              either have one or no contact with another atom (see
              `refatm_diff_selatm`).  For this reason, the number of
              refatm-selatm pairs ``y`` is equal to the total number of
              refatm-selatm contacts, which is
              ``np.sum(refatm_selatm * np.arange(len(refatm_selatm)))``
        
        * `refatm_selres_pair`: Histogram of "bonds" (contacts) between
          refatm-selres pairs.  A refatm-selres pair is defined as a
          reference atom and a selection residue that are connected with
          each other via at least one "bond".
            
            - The first element is meaningless (a refatm-selres pair
              with zero "bonds" is not a pair) and therefore set to zero.
              The second element is the number of refatm-selres pairs
              connected via exactly one "bond", the third element is the
              number of refatm-selres pairs connected via exactly two
              "bonds", and so on.
            - Note that the sum of all histogram elements might exceed
              the number of reference atoms, because a single reference
              atom can be connected to different selection residues with
              different numbers of "bonds".  Even each histogram element
              on its own might exceed the number of reference atoms,
              because a single reference atom can be connected to
              different selection residues with the same number of
              "bonds".
            - Complementary to `refatm_same_selres`.
        
        * `refres_selatm_pair`: Histogram of "bonds" (contacts) between
          refres-selatm pairs.  A refres-selatm pair is defined as a
          reference residue and a selection atom that are connected with
          each other via at least one "bond".
            
            - The first element is meaningless and set to zero.  The
              second element is the number of refres-selatm pairs
              connected via exactly one "bond", the third element is the
              number of refres-selatm pairs connected via exactly two
              "bonds", and so on.
            - Note that the sum of all histogram elements might exceed
              the number of reference residues, because a single
              reference residue can be connected to different selection
              atoms with different numbers of "bonds".  Even each
              histogram element on its own might exceed the number of
              reference residues, because a single reference residue can
              be connected to different selection atoms with the same
              number of "bonds".
            - Complementary to `refres_same_selatm`.
        
        * `refres_selres_pair`: Histogram of "bonds" (contacts) between
          refres-selres pairs.  A refres-selres pair is defined as a
          reference residue and a selection residue that are connected
          with each other via at least one "bond" (contact).
            
            - The first element is meaningless and set to zero.  The
              second element is the number of refres-selres pairs
              connected via exactly one "bond", the third element is the
              number of refres-selres pairs connected via exactly two
              "bonds", and so on.
            - Note that the sum of all histogram elements might exceed
              the number of reference residues, because a single
              reference residue can be connected to different selection
              residues with different numbers of "bonds".  Even each
              histogram element on its own might exceed the number of
              reference residues, because a single reference residue can
              be connected to different selection residues with the same
              number of "bonds".
            - Complementary to `refres_same_selres`.
    """
    if cutoff <= 0:
        warnings.warn("'cutoff' ({}) is equal to or less than zero."
                      .format(cutoff), RuntimeWarning)
    if expected_max_contacts <= 0:
        expected_max_contacts = 16
    if ref.n_atoms == 0:
        return tuple([np.array([0]) for i in range(11)])
    if sel.n_atoms == 0 or cutoff <= 0:
        return tuple([np.array([ref.n_atoms]) for i in range(3)] +
                     [np.array([ref.n_residues]) for i in range(5)] +
                     [np.array([0]) for i in range(3)])
    
    refatm_selatm = np.zeros(expected_max_contacts, dtype=np.uint32)
    refatm_diff_selres = np.zeros(expected_max_contacts, dtype=np.uint32)
    refatm_same_selres = np.zeros(expected_max_contacts, dtype=np.uint32)
    refres_diff_selatm = np.zeros(ref.n_residues, dtype=np.uint32)
    refres_selatm_tot = np.zeros(ref.n_residues, dtype=np.uint32)
    refres_diff_selres = np.zeros(ref.n_residues, dtype=np.uint32)
    refatm_selres_pair = np.zeros(expected_max_contacts, dtype=np.uint32)
    refres_selatm_pair = np.zeros((ref.n_residues, sel.n_atoms),
                                  dtype=np.uint32)
    refres_selres_pair = np.zeros((ref.n_residues, sel.n_residues),
                                  dtype=np.uint32)
    selatm_unused = np.ones((ref.n_residues, sel.n_atoms), dtype=bool)
    selres_unused = np.ones((ref.n_residues, sel.n_residues), dtype=bool)
    unique_refresids = np.unique(ref.resids)
    unique_selresids = np.unique(sel.resids)
    
    for refatm in ref.atoms:
        sel_near_ref = mdt.select.atoms_around_point(
            ag=sel,
            point=refatm.position,
            cutoff=cutoff)
        # refatm_selatm and refatm_diff_selres
        refatm_selatm = mdt.nph.extend(refatm_selatm,
                                       sel_near_ref.n_atoms+1)
        refatm_selatm[sel_near_ref.n_atoms] += 1
        refatm_diff_selres = mdt.nph.extend(refatm_diff_selres,
                                            sel_near_ref.n_residues+1)
        refatm_diff_selres[sel_near_ref.n_residues] += 1
        # refatm_same_selres and refatm_selres_pair
        selresids, selresids_counts = np.unique(sel_near_ref.resids,
                                                return_counts=True)
        if selresids.size == 0:
            refatm_same_selres[0] += 1
        else:
            selresids_counts_max = np.max(selresids_counts)
            refatm_same_selres = mdt.nph.extend(refatm_same_selres,
                                                selresids_counts_max+1)
            refatm_same_selres[selresids_counts] += 1
            refatm_selres_pair = mdt.nph.extend(refatm_selres_pair,
                                                selresids_counts_max+1)
            np.add.at(refatm_selres_pair, selresids_counts, 1)
        # refres_selatm_tot
        refresid = np.searchsorted(unique_refresids, refatm.resid)
        refres_selatm_tot[refresid] += sel_near_ref.n_atoms
        # refres_diff_selatm and refres_selatm_pair
        selatmids = np.intersect1d(sel.ids,
                                   sel_near_ref.ids,
                                   assume_unique=True,
                                   return_indices=True)[1]
        n_atoms = np.count_nonzero(selatm_unused[refresid][selatmids])
        selatm_unused[refresid][selatmids] = False
        refres_diff_selatm[refresid] += n_atoms
        refres_selatm_pair[refresid][selatmids] += 1
        # refres_diff_selres and refres_selres_pair
        selresids = np.intersect1d(unique_selresids,
                                   selresids,
                                   assume_unique=True,
                                   return_indices=True)[1]
        n_residues = np.count_nonzero(selres_unused[refresid][selresids])
        selres_unused[refresid][selresids] = False
        refres_diff_selres[refresid] += n_residues
        np.add.at(refres_selres_pair[refresid],
                  selresids,
                  selresids_counts)
    del selatm_unused, selres_unused, unique_refresids, unique_selresids
    del refresid, selatmids, selresids, selresids_counts
    
    # refres_same_selatm
    max_contacts = np.max(refres_selatm_pair) + 1
    refres_same_selatm = np.zeros(max_contacts, dtype=np.uint32)
    tmp1 = np.zeros_like(refres_selatm_pair, dtype=bool)
    tmp2 = np.zeros(ref.n_residues, dtype=bool)
    for n in range(1, max_contacts):
        np.equal(refres_selatm_pair, n, out=tmp1)       # refres-selatm pair has n contacts
        np.any(tmp1, axis=1, out=tmp2)                  # refres has n contacts with any selatm
        refres_same_selatm[n] = np.count_nonzero(tmp2)  # Number of refres having n contacts with any selatm
    refres_same_selatm[0] = ref.n_residues
    refres_same_selatm[0] -= np.count_nonzero(np.any(refres_selatm_pair,
                                                     axis=1))
    del tmp1, tmp2
    # refres_same_selres
    max_contacts = np.max(refres_selres_pair) + 1
    refres_same_selres = np.zeros(max_contacts, dtype=np.uint32)
    tmp1 = np.zeros_like(refres_selres_pair, dtype=bool)
    tmp2 = np.zeros(ref.n_residues, dtype=bool)
    for n in range(1, max_contacts):
        np.equal(refres_selres_pair, n, out=tmp1)       # refres-selres pair has n contacts
        np.any(tmp1, axis=1, out=tmp2)                  # refres has n contacts with any selres
        refres_same_selres[n] = np.count_nonzero(tmp2)  # Number of refres having n contacts with any selres
    refres_same_selres[0] = ref.n_residues
    refres_same_selres[0] -= np.count_nonzero(np.any(refres_selres_pair,
                                                     axis=1))
    del tmp1, tmp2
    
    refres_diff_selatm = np.bincount(refres_diff_selatm)
    refres_diff_selatm = refres_diff_selatm.astype(np.uint32)
    refres_selatm_tot = np.bincount(refres_selatm_tot)
    refres_selatm_tot = refres_selatm_tot.astype(np.uint32)
    refres_diff_selres = np.bincount(refres_diff_selres)
    refres_diff_selres = refres_diff_selres.astype(np.uint32)
    refres_selatm_pair = np.bincount(refres_selatm_pair.flat)
    refres_selatm_pair = refres_selatm_pair.astype(np.uint32)
    refres_selatm_pair[0] = 0
    refres_selres_pair = np.bincount(refres_selres_pair.flat)
    refres_selres_pair = refres_selres_pair.astype(np.uint32)
    refres_selres_pair[0] = 0
    
    length = max(len(refatm_selatm),
                 len(refatm_diff_selres),
                 len(refatm_same_selres),
                 len(refres_diff_selatm),
                 len(refres_same_selatm),
                 len(refres_selatm_tot),
                 len(refres_diff_selres),
                 len(refres_same_selres),
                 len(refatm_selres_pair),
                 len(refres_selatm_pair),
                 len(refres_selres_pair))
    refatm_selatm = mdt.nph.extend(refatm_selatm, length)
    refatm_diff_selres = mdt.nph.extend(refatm_diff_selres, length)
    refatm_same_selres = mdt.nph.extend(refatm_same_selres, length)
    refres_diff_selatm = mdt.nph.extend(refres_diff_selatm, length)
    refres_same_selatm = mdt.nph.extend(refres_same_selatm, length)
    refres_selatm_tot = mdt.nph.extend(refres_selatm_tot, length)
    refres_diff_selres = mdt.nph.extend(refres_diff_selres, length)
    refres_same_selres = mdt.nph.extend(refres_same_selres, length)
    refatm_selres_pair = mdt.nph.extend(refatm_selres_pair, length)
    refres_selatm_pair = mdt.nph.extend(refres_selatm_pair, length)
    refres_selres_pair = mdt.nph.extend(refres_selres_pair, length)
    
    if debug:
        if np.sum(refatm_selatm) != ref.n_atoms:
            raise ValueError("The sum over 'refatm_selatm' ({}) is not"
                             " equal to the number of reference atoms"
                             " ({})".format(np.sum(refatm_selatm),
                                            ref.n_atoms))
        if np.sum(refatm_diff_selres) != ref.n_atoms:
            raise ValueError("The sum over 'refatm_diff_selres' ({}) is"
                             " not equal to the number of reference"
                             " atoms ({})"
                             .format(np.sum(refatm_diff_selres),
                                     ref.n_atoms))
        if np.sum(refatm_same_selres) < ref.n_atoms:
            raise ValueError("The sum over 'refatm_same_selres' ({}) is"
                             " less than the number of reference atoms"
                             " ({})".format(np.sum(refatm_same_selres),
                                            ref.n_atoms))
        if np.any(refatm_same_selres > ref.n_atoms):
            raise ValueError("At least one element of"
                             " 'refatm_same_selres' is greater than the"
                             " number of reference atoms ({})"
                             .format(ref.n_atoms))
        if np.sum(refres_diff_selatm) != ref.n_residues:
            raise ValueError("The sum over 'refres_diff_selatm' ({}) is"
                             " not equal to the number of reference"
                             " residues ({})"
                             .format(np.sum(refres_diff_selatm),
                                     ref.n_residues))
        if np.sum(refres_same_selatm) < ref.n_residues:
            raise ValueError("The sum over 'refres_same_selatm' ({}) is"
                             " less than the number of reference"
                             " residues ({})"
                             .format(np.sum(refres_same_selatm),
                                     ref.n_residues))
        if np.any(refres_same_selatm > ref.n_residues):
            raise ValueError("At least one element of"
                             " 'refres_same_selatm' is greater than the"
                             " number of reference residues ({})"
                             .format(ref.n_residues))
        if np.sum(refres_selatm_tot) != ref.n_residues:
            raise ValueError("The sum over 'refres_selatm_tot' ({}) is"
                             " not equal to the number of reference"
                             " residues ({})"
                             .format(np.sum(refres_selatm_tot),
                                     ref.n_residues))
        if np.sum(refres_diff_selres) != ref.n_residues:
            raise ValueError("The sum over 'refres_diff_selres' ({}) is"
                             " not equal to the number of reference"
                             " residues ({})"
                             .format(np.sum(refres_diff_selres),
                                     ref.n_residues))
        if np.sum(refres_same_selres) < ref.n_residues:
            raise ValueError("The sum over 'refres_same_selres' ({}) is"
                             " less than the number of reference"
                             " residues ({})"
                             .format(np.sum(refres_same_selres),
                                     ref.n_residues))
        if np.any(refres_same_selres > ref.n_residues):
            raise ValueError("At least one element of"
                             " 'refres_same_selres' is greater than the"
                             " number of reference residues ({})"
                             .format(ref.n_residues))
        
        if refatm_diff_selres[0] != refatm_selatm[0]:
            raise ValueError("The number of ref atoms having no contact"
                             " with any sel atom is not the same in"
                             " 'refatm_diff_selres' ({}) and"
                             " 'refatm_selatm' ({})"
                             .format(refatm_diff_selres[0],
                                     refatm_selatm[0]))
        if refatm_same_selres[0] != refatm_selatm[0]:
            raise ValueError("The number of ref atoms having no contact"
                             " with any sel atom is not the same in"
                             " 'refatm_same_selres' ({}) and"
                             " 'refatm_selatm' ({})"
                             .format(refatm_same_selres[0],
                                     refatm_selatm[0]))
        if refres_same_selatm[0] != refres_diff_selatm[0]:
            raise ValueError("The number of ref residues having no"
                             " contact with any sel atom is not the"
                             " same in 'refres_same_selatm' ({}) and"
                             " 'refres_diff_selatm' ({})"
                             .format(refres_same_selatm[0],
                                     refres_diff_selatm[0]))
        if refres_selatm_tot[0] != refres_diff_selatm[0]:
            raise ValueError("The number of ref residues having no"
                             " contact with any sel atom is not the"
                             " same in 'refres_selatm_tot' ({}) and"
                             " 'refres_diff_selatm' ({})"
                             .format(refres_selatm_tot[0],
                                     refres_diff_selatm[0]))
        if refres_diff_selres[0] != refres_diff_selatm[0]:
            raise ValueError("The number of ref residues having no"
                             " contact with any sel atom is not the"
                             " same in 'refres_diff_selres' ({}) and"
                             " 'refres_diff_selatm' ({})"
                             .format(refres_diff_selres[0],
                                     refres_diff_selatm[0]))
        if refres_same_selres[0] != refres_diff_selatm[0]:
            raise ValueError("The number of ref residues having no"
                             " contact with any sel atom is not the"
                             " same in 'refres_same_selres' ({}) and"
                             " 'refres_diff_selatm' ({})"
                             .format(refres_same_selres[0],
                                     refres_diff_selatm[0]))
        if refatm_selres_pair[0] != 0:
            raise ValueError("The first element of 'refatm_selres_pair'"
                             " ({}) is not zero"
                             .format(refatm_selres_pair[0]))
        if refres_selatm_pair[0] != 0:
            raise ValueError("The first element of 'refres_selatm_pair'"
                             " ({}) is not zero"
                             .format(refres_selatm_pair[0]))
        if refres_selres_pair[0] != 0:
            raise ValueError("The first element of 'refres_selres_pair'"
                             " ({}) is not zero"
                             .format(refres_selres_pair[0]))
        
        refatm_selatm_tot_contacts = np.sum(
            refatm_selatm * np.arange(len(refatm_selatm))
        )
        _, natms_per_refres = np.unique(ref.resindices,
                                        return_counts=True)
        if np.all(natms_per_refres == 1):
            # refres == refatm
            # * refatm_selatm == refatm_diff_selatm == refatm_selatm_tot == refatm_selres_tot
            #                    refres_diff_selatm    refres_selatm_tot == refres_selres_tot
            # * refatm_same_selatm == [x, Nrefatm-x]
            #   refres_same_selatm
            # * refatm_diff_selres
            #   refres_diff_selres
            # * refatm_same_selres
            #   refres_same_selres
            # * refatm_selatm_pair == [0, y]
            #   refres_selatm_pair
            # * refatm_selres_pair
            #   refres_selres_pair
            if np.any(refres_diff_selatm != refatm_selatm):
                raise ValueError("refres = refatm, but"
                                 " 'refres_diff_selatm'"
                                 " != 'refatm_selatm'")
            if np.any(refres_selatm_tot != refatm_selatm):
                raise ValueError("refres = refatm, but "
                                 " 'refres_selatm_tot'"
                                 " != 'refatm_selatm'")
            if np.any(refres_same_selatm[:2] !=
                      np.array([refatm_selatm[0],
                                ref.n_atoms-refatm_selatm[0]])):
                raise ValueError("refres = refatm, but"
                                 " 'refres_same_selatm' !="
                                 " [x, Nrefatm-x]")
            if np.sum(refres_same_selatm) != ref.n_atoms:
                raise ValueError("refres = refatm, but the sum over"
                                 " 'refres_same_selatm' ({}) is not"
                                 " equal to the number of reference"
                                 " atoms ({})"
                                 .format(np.sum(refres_same_selatm),
                                         ref.n_atoms))
            if np.any(refres_diff_selres != refatm_diff_selres):
                raise ValueError("refres = refatm, but"
                                 " 'refres_diff_selres' !="
                                 " 'refatm_diff_selres'")
            if np.any(refres_same_selres != refatm_same_selres):
                raise ValueError("refres = refatm, but"
                                 " 'refres_same_selres' !="
                                 " 'refatm_same_selres'")
            if np.any(np.delete(refres_selatm_pair, 1) != 0):
                raise ValueError("refres = refatm, but"
                                 " 'refres_selatm_pair' != [0, y]")
            if refres_selatm_pair[1] != refatm_selatm_tot_contacts:
                raise ValueError("refres = refatm, but"
                                 " 'refres_selatm_pair' != [0, y]")
            if np.any(refres_selres_pair != refatm_selres_pair):
                raise ValueError("refres = refatm, but"
                                 " 'refres_selres_pair' !="
                                 " 'refatm_selres_pair'")
        
        _, natms_per_selres = np.unique(sel.resindices,
                                        return_counts=True)
        if np.all(natms_per_selres == 1):
            # selres == selatm
            # * refatm_selatm == refatm_diff_selatm == refatm_selatm_tot == refatm_selres_tot
            #                    refatm_diff_selres
            # * refatm_same_selatm == [x, Nrefatm-x]
            #   refatm_same_selres
            # * refres_diff_selatm
            #   refres_diff_selres
            # * refres_same_selatm
            #   refres_same_selres
            # * refres_selatm_tot == refres_selres_tot
            # * refatm_selatm_pair == [0, y]
            #   refatm_selres_pair
            # * refres_selatm_pair
            #   refres_selres_pair
            if np.any(refatm_diff_selres != refatm_selatm):
                raise ValueError("selres = selatm, but"
                                 " 'refatm_diff_selres' !="
                                 " 'refatm_selatm'")
            if np.any(refatm_same_selres[:2] !=
                      np.array([refatm_selatm[0],
                                ref.n_atoms-refatm_selatm[0]])):
                raise ValueError("selres = selatm, but"
                                 " 'refatm_same_selres' !="
                                 " [x, Nrefatm-x]")
            if np.sum(refatm_same_selres) != ref.n_atoms:
                raise ValueError("selres = selatm, but the sum over"
                                 " 'refatm_same_selres' ({}) is not"
                                 " equal to the number of reference"
                                 " atoms ({})"
                                 .format(np.sum(refatm_same_selres),
                                         ref.n_atoms))
            if np.any(refres_diff_selres != refres_diff_selatm):
                raise ValueError("selres = selatm, but"
                                 " 'refres_diff_selres' !="
                                 " 'refres_diff_selatm'")
            if np.any(refres_same_selres != refres_same_selatm):
                raise ValueError("selres = selatm, but"
                                 " 'refres_same_selres' !="
                                 " 'refres_same_selatm'")
            if np.any(np.delete(refatm_selres_pair, 1) != 0):
                raise ValueError("refres = refatm, but"
                                 " 'refatm_selres_pair' != [0, y]")
            if refatm_selres_pair[1] != refatm_selatm_tot_contacts:
                raise ValueError("refres = refatm, but"
                                 " 'refatm_selres_pair' != [0, y]")
            if np.any(refres_selres_pair != refres_selatm_pair):
                raise ValueError("refres = refatm, but"
                                 " 'refres_selres_pair' !="
                                 " 'refres_selatm_pair'")
        
        if (refatm_diff_selres.shape != refatm_selatm.shape or
            refatm_same_selres.shape != refatm_selatm.shape or
            refres_diff_selatm.shape != refatm_selatm.shape or
            refres_same_selatm.shape != refatm_selatm.shape or
            refres_selatm_tot.shape != refatm_selatm.shape or
            refres_diff_selres.shape != refatm_selatm.shape or
            refres_same_selres.shape != refatm_selatm.shape or
            refatm_selres_pair.shape != refatm_selatm.shape or
            refres_selatm_pair.shape != refatm_selatm.shape or
            refres_selres_pair.shape != refatm_selatm.shape):
            raise ValueError("The histograms have not the same shape:\n"
                             "  refatm_selatm.shape = {}\n"
                             "  refatm_diff_selres.shape = {}\n"
                             "  refatm_same_selres.shape = {}\n"
                             "  refres_diff_selatm.shape = {}\n"
                             "  refres_same_selatm.shape = {}\n"
                             "  refres_selatm_tot.shape = {}\n"
                             "  refres_diff_selres.shape = {}\n"
                             "  refres_same_selres.shape = {}\n"
                             "  refatm_selres_pair.shape = {}\n"
                             "  refres_selatm_pair.shape = {}\n"
                             "  refres_selres_pair.shape = {}"
                             .format(refatm_selatm.shape,
                                     refatm_diff_selres.shape,
                                     refatm_same_selres.shape,
                                     refres_diff_selatm.shape,
                                     refres_same_selatm.shape,
                                     refres_selatm_tot.shape,
                                     refres_diff_selres.shape,
                                     refres_same_selres.shape,
                                     refatm_selres_pair.shape,
                                     refres_selatm_pair.shape,
                                     refres_selres_pair.shape))
    
    return (refatm_selatm,
            refatm_diff_selres,
            refatm_same_selres,
            refres_diff_selatm,
            refres_same_selatm,
            refres_selatm_tot,
            refres_diff_selres,
            refres_same_selres,
            refatm_selres_pair,
            refres_selatm_pair,
            refres_selres_pair)


if __name__ == '__main__':
    timer_tot = datetime.now()
    proc = psutil.Process(os.getpid())
    proc.cpu_percent()  # Initiate monitoring of CPU usage
    parser = argparse.ArgumentParser(
        description=(
            "Calculate the number of contacts between two atom groups."
            "  Contacts are counted by looping over all atoms of the"
            " reference group and searching for atoms of the selection"
            " group that are within the given cutoff.  Contacts are"
            " binned according to how many different selection"
            " atoms/residues have contact with a given reference"
            " atom/residue and according to how many contacts exist"
            " between a given selection-residue/atom"
            " reference-atom/residue pair.  The results are stored in"
            " histograms."
        )
    )
    parser.add_argument(
        '-f',
        dest='TRJFILE',
        type=str,
        required=True,
        help="Trajectory file.  See supported coordinate formats of"
             " MDAnalysis."
    )
    parser.add_argument(
        '-s',
        dest='TOPFILE',
        type=str,
        required=True,
        help="Topology file.  See supported topology formats of"
             " MDAnalysis."
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
        help="First frame to read from the trajectory.  Frame numbering"
             " starts at zero.  Default: %(default)s."
    )
    parser.add_argument(
        '-e',
        dest='END',
        type=int,
        required=False,
        default=-1,
        help="Last frame to read from the trajectory.  This is"
             " exclusive, i.e. the last frame read is actually END-1."
             "  A value of -1 means to read the very last frame."
             "  Default: %(default)s."
    )
    parser.add_argument(
        '--every',
        dest='EVERY',
        type=int,
        required=False,
        default=1,
        help="Read every n-th frame from the trajectory.  Default:"
             " %(default)s."
    )
    parser.add_argument(
        '--ref',
        dest='REF',
        type=str,
        nargs='+',
        required=True,
        help="Selection string for the reference group.  See MDAnalysis'"
             " selection syntax for possible choices.  Example:"
             " 'name Li'."
    )
    parser.add_argument(
        "--sel",
        dest="SEL",
        type=str,
        nargs="+",
        required=True,
        help="Selection string for the selection group.  See MDAnalysis'"
             " selection syntax for possible choices.  Example:"
             " 'type OE'."
    )
    parser.add_argument(
        '-c',
        dest='CUTOFF',
        type=float,
        required=True,
        help="Cutoff distance in Angstrom.  A contact between a"
             " reference and selection atom is counted, if their"
             " distance is less than or equal to this cutoff."
    )
    parser.add_argument(
        '--updating-ref',
        dest='UPDATING_REF',
        required=False,
        default=False,
        action='store_true',
        help="Use an updating atom group for the reference group."
             "  Selection expressions of updating atom groups are"
             " re-evaluated every time step.  E.g. useful for position"
             " based selections like 'type Li and prop z <= 2.0'."
    )
    parser.add_argument(
        '--updating-sel',
        dest='UPDATING_SEL',
        required=False,
        default=False,
        action='store_true',
        help="Use an updating atom group for the selection group."
    )
    parser.add_argument(
        '--debug',
        dest='DEBUG',
        required=False,
        default=False,
        action='store_true',
        help="Run in debug mode."
    )
    args = parser.parse_args()
    print(mdt.rti.run_time_info_str())
    if args.CUTOFF <= 0:
        raise ValueError("-c ({}) must be positive".format(args.CUTOFF))
    
    print("\n")
    u = mdt.select.universe(top=args.TOPFILE, trj=args.TRJFILE)
    print("\n")
    print("Creating selections...")
    timer = datetime.now()
    ref = u.select_atoms(' '.join(args.REF), updating=args.UPDATING_REF)
    sel = u.select_atoms(' '.join(args.SEL), updating=args.UPDATING_SEL)
    if ref.n_atoms == 0 and not args.UPDATING_REF:
        raise ValueError("The reference group contains no atoms")
    if sel.n_atoms == 0 and not args.UPDATING_SEL:
        raise ValueError("The selection group contains no atoms")
    print("Reference group: '{}'".format(' '.join(args.REF)))
    print(mdt.rti.ag_info_str(ag=ref, indent=2))
    print("Selection group: '{}'".format(' '.join(args.SEL)))
    print(mdt.rti.ag_info_str(ag=sel, indent=2))
    print("Elapsed time:         {}".format(datetime.now()-timer))
    print("Current memory usage: {:.2f} MiB"
          .format(proc.memory_info().rss/2**20))
    print("\n")
    BEGIN, END, EVERY, N_FRAMES = mdt.check.frame_slicing(
        start=args.BEGIN,
        stop=args.END,
        step=args.EVERY,
        n_frames_tot=u.trajectory.n_frames
    )
    
    expected_max_contacts = 16  # Will be increased if necessary
    hist_atm = np.zeros((3, expected_max_contacts), dtype=np.uint32)
    hist_res = np.zeros((5, expected_max_contacts), dtype=np.uint32)
    hist_par = np.zeros((3, expected_max_contacts), dtype=np.uint32)
    if args.UPDATING_REF:
        n_refatm = 0
        n_refres = 0
    if args.UPDATING_SEL:
        n_selatm = 0
        n_selres = 0
    n_pairs = np.zeros(hist_par.shape[0], dtype=np.uint32)
    n_pairs_tmp = np.zeros_like(n_pairs)
    
    print("\n")
    print("Reading trajectory...")
    print("Total number of frames: {:>8d}".format(u.trajectory.n_frames))
    print("Frames to read:         {:>8d}".format(N_FRAMES))
    print("First frame to read:    {:>8d}".format(BEGIN))
    print("Last frame to read:     {:>8d}".format(END-1))
    print("Read every n-th frame:  {:>8d}".format(EVERY))
    print("Time first frame:       {:>12.3f} (ps)"
          .format(u.trajectory[BEGIN].time))
    print("Time last frame:        {:>12.3f} (ps)"
          .format(u.trajectory[END-1].time))
    print("Time step first frame:  {:>12.3f} (ps)"
          .format(u.trajectory[BEGIN].dt))
    print("Time step last frame:   {:>12.3f} (ps)"
          .format(u.trajectory[END-1].dt))
    timer = datetime.now()
    trj = mdt.rti.ProgressBar(u.trajectory[BEGIN:END:EVERY])
    for ts in trj:
        if args.UPDATING_REF:
            n_refatm += ref.n_atoms
            n_refres += ref.n_residues
        if args.UPDATING_SEL:
            n_selatm += sel.n_atoms
            n_selres += sel.n_residues
        if ref.n_atoms == 0:
            continue
        hist_tmp = np.asarray(contact_hist(
            ref=ref,
            sel=sel,
            cutoff=args.CUTOFF,
            expected_max_contacts=hist_atm.shape[1],
            debug=args.DEBUG
        ))
        hist_atm, hist_atm_tmp = mdt.nph.match_shape(hist_atm,
                                                     hist_tmp[:3])
        hist_atm += hist_atm_tmp
        hist_res, hist_res_tmp = mdt.nph.match_shape(hist_res,
                                                     hist_tmp[3:8])
        hist_res += hist_res_tmp
        hist_par, hist_par_tmp = mdt.nph.match_shape(hist_par,
                                                     hist_tmp[8:])
        hist_par += hist_par_tmp
        np.sum(hist_tmp[8:], axis=1, out=n_pairs_tmp)
        n_pairs += n_pairs_tmp
        progress_bar_mem = proc.memory_info().rss / 2**20
        trj.set_postfix_str("{:>7.2f}MiB".format(progress_bar_mem),
                            refresh=False)
    trj.close()
    print("Elapsed time:         {}".format(datetime.now()-timer))
    print("Current memory usage: {:.2f} MiB"
          .format(proc.memory_info().rss/2**20))
    
    if args.UPDATING_REF and n_refatm == 0:
        warnings.warn("The total number of reference atoms is zero. The"
                      " output will be meaningless", RuntimeWarning)
    if args.UPDATING_SEL and n_selatm == 0:
        warnings.warn("The total number of selection atoms is zero. The"
                      " output will be meaningless", RuntimeWarning)
    if not args.UPDATING_REF:
        n_refatm = ref.n_atoms * N_FRAMES
        n_refres = ref.n_residues * N_FRAMES
    if not args.UPDATING_SEL:
        n_selatm = sel.n_atoms * N_FRAMES
        n_selres = sel.n_residues * N_FRAMES
    hist_atm = hist_atm / n_refatm
    hist_res = hist_res / n_refres
    hist_par = hist_par / n_pairs[:,None]
    
    av_atm = np.zeros(2, dtype=np.float64)
    av_atm_bound = np.zeros(2, dtype=np.float64)
    for i in [0, 1]:  # 0 = refatm_selatm; 1 = refatm_diff_selres
        # Average refatm-selatm coordination number normalized by the
        # total number of refatms:
        av_atm[i] = np.sum(hist_atm[i] * np.arange(len(hist_atm[i])))
        # Average refatm-selatm coordination number normalized by the
        # number of refatms that are bound to at least one selatm
        av_atm_bound[i] = av_atm[i] / (1 - hist_atm[i][0])
    av_res = np.zeros(4, dtype=np.float64)
    av_res_bound = np.zeros(4, dtype=np.float64)
    for i in [0, 2, 3]:  # 0 = refres_diff_selatm; 2 = refres_selatm_tot; 3 = refres_diff_selres
        av_res[i] = np.sum(hist_res[i] * np.arange(len(hist_res[i])))
        av_res_bound[i] = av_res[i] / (1 - hist_res[i][0])
    av_par = np.zeros(3, dtype=np.float64)
    av_par_bound = np.zeros(3, dtype=np.float64)
    for i in [0]:  # 0 = refatm_selres_pair
        # Average number of bonds between refatm-selres pairs normalized
        # by the number of refatm-selres pairs:
        av_par_bound[i] = np.sum(hist_par[i] * np.arange(len(hist_par[i])))
        # Multiplied by the percentage of bound refatms
        av_par[i] = av_par_bound[i] * (1 - hist_atm[0][0])
    for i in [1, 2]:  # 1 = refres_selatm_pair; 2 = refres_selres_pair
        av_par_bound[i] = np.sum(hist_par[i] * np.arange(len(hist_par[i])))
        av_par[i] = av_par_bound[i] * (1 - hist_res[0][0])
    
    last_nonzero = 0
    if not np.all(hist_atm == 0):
        last_nonzero = max(last_nonzero, np.max(np.nonzero(hist_atm)[1]))
    if not np.all(hist_res == 0):
        last_nonzero = max(last_nonzero, np.max(np.nonzero(hist_res)[1]))
    if not np.all(hist_par == 0):
        last_nonzero = max(last_nonzero, np.max(np.nonzero(hist_par)[1]))
    
    print("\n")
    print("Creating output...")
    timer = datetime.now()
    mdt.fh.write_header(args.OUTFILE)
    with open(args.OUTFILE, 'a') as outfile:
        outfile.write("# \n")
        outfile.write("# \n")
        outfile.write("# Reference: '{}'\n".format(' '.join(args.REF)))
        outfile.write(mdt.fh.indent(text=mdt.rti.ag_info_str(ag=ref),
                                    amount=1,
                                    char="#   ")
                      + "\n")
        outfile.write("# \n")
        outfile.write("# Selection: '{}'\n".format(' '.join(args.SEL)))
        outfile.write(mdt.fh.indent(text=mdt.rti.ag_info_str(ag=sel),
                                    amount=1,
                                    char="#   ")
                      + "\n")
        outfile.write("# \n")
        outfile.write("# \n")
        outfile.write("# Contact histograms\n")
        outfile.write("# Cutoff (Angstrom): {}\n".format(args.CUTOFF))
        outfile.write("# Statistics:\n")
        outfile.write("#   Number of frames:                         {:>9d}\n".format(N_FRAMES))
        outfile.write("#   Total number of ref atoms    (per frame): {:>9d}  ({:>9.2f})\n".format(n_refatm, n_refatm/N_FRAMES))
        outfile.write("#   Total number of ref residues (per frame): {:>9d}  ({:>9.2f})\n".format(n_refres, n_refres/N_FRAMES))
        outfile.write("#   Total number of sel atoms    (per frame): {:>9d}  ({:>9.2f})\n".format(n_selatm, n_selatm/N_FRAMES))
        outfile.write("#   Total number of sel residues (per frame): {:>9d}  ({:>9.2f})\n".format(n_selres, n_selres/N_FRAMES))
        outfile.write("# \n")
        outfile.write("# \n")
        outfile.write("# Percentage of ref atoms    connected to at least one sel atom:                    {:10.4e}\n".format(1-hist_atm[0][0]))
        outfile.write("# Percentage of ref residues connected to at least one sel atom:                    {:10.4e}\n".format(1-hist_res[0][0]))
        outfile.write("#    (2)  Average       sel atom    coordination number of all   ref atoms:         {:10.4e}  (Every ref atom                              has on average           contact  with this many           sel atoms)\n".format(av_atm[0]))
        outfile.write("#    (2)* Average       sel atom    coordination number of bound ref atoms:         {:10.4e}  (Every ref atom    connected to sel atoms    has on average           contact  with this many           sel atoms)\n".format(av_atm_bound[0]))
        outfile.write("#    (3)  Average       sel residue coordination number of all   ref atoms:         {:10.4e}  (Every ref atom                              has on average           contact  with this many different sel residues)\n".format(av_atm[1]))
        outfile.write("#    (3)* Average       sel residue coordination number of bound ref atoms:         {:10.4e}  (Every ref atom    connected to sel residues has on average           contact  with this many different sel residues)\n".format(av_atm_bound[1]))
        outfile.write("#    (5)  Average       sel atom    coordination number of all   ref residues:      {:10.4e}  (Every ref residue                           has on average           contact  with this many different sel atoms)\n".format(av_res[0]))
        outfile.write("#    (5)* Average       sel atom    coordination number of bound ref residues:      {:10.4e}  (Every ref residue connected to sel atoms    has on average           contact  with this many different sel atoms)\n".format(av_res_bound[0]))
        outfile.write("#    (7)  Average total sel atom    coordination number of all   ref residues:      {:10.4e}  (Every ref residue                           has on average this many contacts with                     sel atoms)\n".format(av_res[2]))
        outfile.write("#    (7)* Average total sel atom    coordination number of bound ref residues:      {:10.4e}  (Every ref residue connected to sel atoms    has on average this many contacts with                     sel atoms)\n".format(av_res_bound[2]))
        outfile.write("#    (8)  Average       sel residue coordination number of all   ref residues:      {:10.4e}  (Every ref residue                           has on average           contact  with this many different sel residues)\n".format(av_res[3]))
        outfile.write("#    (8)* Average       sel residue coordination number of bound ref residues:      {:10.4e}  (Every ref residue connected to sel residues has on average           contact  with this many different sel residues)\n".format(av_res_bound[3]))
        outfile.write("#   (10)' Average number of 'bonds' ref atoms    establish to the same sel residue: {:10.4e}  (Every ref atom                              has on average this many contacts with           the same  sel residue)\n".format(av_par[0]))
        outfile.write("#   (10)  Average number of 'bonds' between ref-atom-   sel-residue pairs:          {:10.4e}  (Every ref atom    connected to sel residues has on average this many contacts with           the same  sel residue)\n".format(av_par_bound[0]))
        outfile.write("#   (11)' Average number of 'bonds' ref residues establish to the same sel atom:    {:10.4e}  (Every ref residue                           has on average this many contacts with           the same  sel atom)\n".format(av_par[1]))
        outfile.write("#   (11)  Average number of 'bonds' between ref-residue-sel-atom    pairs:          {:10.4e}  (Every ref residue connected to sel atoms    has on average this many contacts with           the same  sel atom)\n".format(av_par_bound[1]))
        outfile.write("#   (12)' Average number of 'bonds' ref residues establish to the same sel residue: {:10.4e}  (Every ref residue                           has on average this many contacts with           the same  sel residue)\n".format(av_par[2]))
        outfile.write("#   (12)  Average number of 'bonds' between ref-residue-sel-residue pairs:          {:10.4e}  (Every ref residue connected to sel residues has on average this many contacts with           the same  sel residue)\n".format(av_par_bound[2]))
        outfile.write("# The average coordination numbers given here are the product sum over all histogram elements of column number (i) times their respective number of contacts N\n")
        outfile.write("# *) Additionally divided    by the percentage of bound ref atoms/residues (-> Probabilities are renormalized to the number of bound ref atoms/residues)\n")
        outfile.write("# ') Additionally multiplied by the percentage of bound ref atoms/residues (-> Probabilities are renormalized to the number of all   ref atoms/residues)\n")
        outfile.write("# \n")
        outfile.write("# \n")
        outfile.write("# The columns contain:\n")
        outfile.write("#    1 N:                  Number of contacts between the reference and selection\n")
        outfile.write("#    2 refatm_selatm:      % of ref atoms    that have   contact  with N different sel atoms    (multiple contacts with the same sel atom    discounted) [refatm_diff_selatm]\n")
        outfile.write("#                       [= % of ref atoms    that have N contacts with             sel atoms    (multiple contacts with the same sel atom       counted)  refatm_selatm_tot]\n")
        outfile.write("#                       [= % of ref atoms    that have N contacts with             sel residues (multiple contacts with the same sel residue    counted)  refatm_selres_tot]\n")
        outfile.write("#    3 refatm_diff_selres: % of ref atoms    that have   contact  with N different sel residues (multiple contacts with the same sel residue discounted)\n")
        outfile.write("#    4 refatm_same_selres: % of ref atoms    that have N contacts with   the same  sel residue  (multiple contacts with the same sel residue    counted, multiple connections to different sel residues via the same number of contacts discounted)\n")
        outfile.write("#    5 refres_diff_selatm: % of ref residues that have   contact  with N different sel atoms    (multiple contacts with the same sel atom    discounted)\n")
        outfile.write("#    6 refres_same_selatm: % of ref residues that have N contacts with   the same  sel atom     (multiple contacts with the same sel atom       counted, multiple connections to different sel atoms    via the same number of contacts discounted)\n")
        outfile.write("#    7 refres_selatm_tot:  % of ref residues that have N contacts with             sel atoms    (multiple contacts with the same sel atom       counted)\n")
        outfile.write("#                       [= % of ref residues that have N contacts with             sel residues (multiple contacts with the same sel residue    counted)  refres_selres_tot]\n")
        outfile.write("#    8 refres_diff_selres: % of ref residues that have   contact  with N different sel residues (multiple contacts with the same sel residue discounted)\n")
        outfile.write("#    9 refres_same_selres: % of ref residues that have N contacts with   the same  sel residue  (multiple contacts with the same sel residue    counted, multiple connections to different sel residues via the same number of contacts discounted)\n")
        outfile.write("#   10 refatm_selres_pair: % of ref-atom    sel-residue pairs connected via N 'bonds'         (first element is meaningless)\n")
        outfile.write("#   11 refres_selatm_pair: % of ref-residue sel-atom    pairs connected via N 'bonds'         (first element is meaningless)\n")
        outfile.write("#   12 refres_selres_pair: % of ref-residue sel-residue pairs connected via N 'bonds'         (first element is meaningless)\n")
        outfile.write("# \n")
        outfile.write('# Column number:\n')
        outfile.write("# {:3d}   {:16d} {:16d} {:16d}   {:16d} {:16d} {:16d} {:16d} {:16d}   {:16d} {:16d} {:16d}\n"
                      .format(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12))
        outfile.write("# {:>3s}   {:>16s} {:>16s} {:>16s}   {:>16s} {:>16s} {:>16s} {:>16s} {:>16s}   {:>16s} {:>16s} {:>16s}\n"
                      .format("N",                 # 01
                              "refatm_selatm",     # 02
                              "refatm_d_selres",   # 03
                              "refatm_s_selres",   # 04
                              "refres_d_selatm",   # 05
                              "refres_s_selatm",   # 06
                              "refres_selatm_t",   # 07
                              "refres_d_selres",   # 08
                              "refres_s_selres",   # 09
                              "refatm_selres_p",   # 10
                              "refres_selatm_p",   # 11
                              "refres_selres_p"))  # 12
        for i in range(last_nonzero+1):
            outfile.write("  {:3d}   {:16.9e} {:16.9e} {:16.9e}   {:16.9e} {:16.9e} {:16.9e} {:16.9e} {:16.9e}   {:16.9e} {:16.9e} {:16.9e}\n"
                          .format(i,                # 01
                                  hist_atm[0][i],   # 02
                                  hist_atm[1][i],   # 03
                                  hist_atm[2][i],   # 04
                                  hist_res[0][i],   # 05
                                  hist_res[1][i],   # 06
                                  hist_res[2][i],   # 07
                                  hist_res[3][i],   # 08
                                  hist_res[4][i],   # 09
                                  hist_par[0][i],   # 10
                                  hist_par[1][i],   # 11
                                  hist_par[2][i]))  # 12
        outfile.write("\n")
        outfile.write("\n")
        outfile.write("# Sums\n")
        outfile.write("  {:3d}   {:16.9e} {:16.9e} {:16.9e}   {:16.9e} {:16.9e} {:16.9e} {:16.9e} {:16.9e}   {:16.9e} {:16.9e} {:16.9e}\n"
                      .format(np.sum(np.arange(last_nonzero+1)),  # 01
                              np.sum(hist_atm[0]),                # 02
                              np.sum(hist_atm[1]),                # 03
                              np.sum(hist_atm[2]),                # 04
                              np.sum(hist_res[0]),                # 05
                              np.sum(hist_res[1]),                # 06
                              np.sum(hist_res[2]),                # 07
                              np.sum(hist_res[3]),                # 08
                              np.sum(hist_res[4]),                # 09
                              np.sum(hist_par[0]),                # 10
                              np.sum(hist_par[1]),                # 11
                              np.sum(hist_par[2])))               # 12
        outfile.flush()
    print("Created {}".format(args.OUTFILE))
    print("Elapsed time:         {}".format(datetime.now()-timer))
    print("Current memory usage: {:.2f} MiB"
          .format(proc.memory_info().rss/2**20))
    
    print("\n")
    print("Checking output for consistency...")
    timer = datetime.now()
    tol = 1e-4
    for i in [0, 1]:  # refatm_selatm, refatm_diff_selres
        if not np.isclose(np.sum(hist_atm[i]), 1, rtol=0, atol=tol):
            raise ValueError("The sum over 'hist_atm[{}]' ({}) is not"
                             " one".format(i, np.sum(hist_atm[i])))
    for i in [2]:  # refatm_same_selres
        if np.sum(hist_atm[i]) < 1:
            raise ValueError("The sum over 'hist_atm[{}]' ({}) is less"
                             " than one".format(i, np.sum(hist_atm[i])))
        if np.any(hist_atm[i] > 1):
            raise ValueError("At least one element of 'hist_atm[{}]' is"
                             " greater than one".format(i))
    for i in [0, 2, 3]:  # refres_diff_selatm, refres_selatm_tot, refres_diff_selres
        if not np.isclose(np.sum(hist_res[i]), 1, rtol=0, atol=tol):
            raise ValueError("The sum over 'hist_res[{}]' ({}) is not"
                             " one".format(i, np.sum(hist_res[i])))
    for i in [1, 4]:  # refres_same_selatm, refres_same_selres
        if np.sum(hist_res[i]) < 1:
            raise ValueError("The sum over 'hist_res[{}]' ({}) is less"
                             " than one".format(i, np.sum(hist_res[i])))
        if np.any(hist_res[i]) > 1:
            raise ValueError("At least one element of 'hist_res[{}]' is"
                             " greater than one".format(i))
    for i, hist in enumerate(hist_par):
        if not np.isclose(np.sum(hist), 1, rtol=0, atol=tol):
            raise ValueError("The sum over 'hist_par[{}]' ({}) is not"
                             " one".format(i, np.sum(hist)))
    
    for i in range(1, len(hist_atm)):
        if hist_atm[i][0] != hist_atm[0][0]:
            raise ValueError("The percentage of refatms having no"
                             " contact with any selatm is not the same"
                             " in 'hist_atm[{}][0]' ({}) and"
                             " 'hist_atm[0][0]' ({})"
                             .format(i, hist_atm[i][0], hist_atm[0][0]))
    for i in range(1, len(hist_res)):
        if hist_res[i][0] != hist_res[0][0]:
            raise ValueError("The percentage of refres having no contact"
                             " with any selatm is not the same in"
                             " 'hist_res[{}][0]' ({}) and"
                             " 'hist_res[0][0]' ({})"
                             .format(i, hist_res[i][0], hist_res[0][0]))
    for i in range(1, len(hist_par)):
        if hist_par[i][0] != 0:
            raise ValueError("The first element of 'hist_par[{}][0]'"
                             " ({}) is not zero"
                             .format(i, hist_par[i][0]))
    
    if ref.n_residues > 0 and not args.UPDATING_REF:
        _, natms_per_refres = np.unique(ref.resindices,
                                        return_counts=True)
        if np.all(natms_per_refres == 1):
            # refres == refatm
            if not np.allclose(hist_res[0], hist_atm[0],
                               rtol=0, atol=tol, equal_nan=True):
                # refres_diff_selatm != refatm_selatm
                raise ValueError("refres = refatm, but 'hist_res[0]' !="
                                 " 'hist_atm[0]'")
            if not np.allclose(hist_res[2], hist_atm[0],
                               rtol=0, atol=tol, equal_nan=True):
                # refres_selatm_tot != refatm_selatm
                raise ValueError("refres = refatm, but 'hist_res[2]' !="
                                 " 'hist_atm[0]'")
            if not np.allclose(hist_res[1][:2],           # refres_same_selatm
                               np.array([hist_atm[0][0],  # refatm_selatm
                                         1-hist_atm[0][0]]),
                               rtol=0, atol=tol):
                raise ValueError("refres = refatm, but 'hist_res[1]' !="
                                 " [x, 1-x]")
            if not np.isclose(np.sum(hist_res[1]), 1, rtol=0, atol=tol):  # refres_same_selatm
                raise ValueError("refres = refatm, but the sum over"
                                 " 'hist_res[1]' ({}) is not one"
                                 .format(np.sum(hist_res[1])))
            if not np.allclose(hist_res[3], hist_atm[1],
                               rtol=0, atol=tol, equal_nan=True):
                # refres_diff_selres != refatm_diff_selres
                raise ValueError("refres = refatm, but 'hist_res[3]' !="
                                 " 'hist_atm[1]'")
            if not np.allclose(hist_res[4], hist_atm[2],
                               rtol=0, atol=tol, equal_nan=True):
                # refres_same_selres != refatm_same_selres
                raise ValueError("refres = refatm, but 'hist_res[4]' !="
                                 " 'hist_atm[2]'")
            if not np.isclose(hist_par[1][1], 1, rtol=0, atol=tol):  # refres_selatm_pair
                raise ValueError("refres = refatm, but 'hist_par[1]'"
                                 "  != [0, 1]")
            if not np.isclose(np.sum(hist_par[1]), 1, rtol=0, atol=tol):  # refres_selatm_pair
                raise ValueError("refres = refatm, but the sum over"
                                 " 'hist_par[1]' ({}) is not one"
                                 .format(np.sum(hist_par[1])))
            if not np.allclose(hist_par[2], hist_par[0],
                               rtol=0, atol=tol, equal_nan=True):
                # refres_selres_pair != refatm_selres_pair
                raise ValueError("refres = refatm, but 'hist_par[2]' !="
                                 " 'hist_par[0]'")
    
    if sel.n_residues > 0 and not args.UPDATING_SEL:
        _, natms_per_selres = np.unique(sel.resindices,
                                        return_counts=True)
        if np.all(natms_per_selres == 1):
            # selres == selatm
            if np.any(hist_atm[1] != hist_atm[0]):
                # refatm_diff_selres != refatm_selatm
                raise ValueError("selres = selatm, but 'hist_atm[1]' !="
                                 " 'hist_atm[0]'")
            if not np.allclose(hist_atm[2][:2],           # refatm_same_selres
                               np.array([hist_atm[0][0],  # refatm_selatm
                                         1-hist_atm[0][0]]),
                               rtol=0,
                               atol=tol):
                raise ValueError("selres = selatm, but 'hist_atm[2]' !="
                                 " '[x, 1-x]'")
            if not np.isclose(np.sum(hist_atm[2]), 1, rtol=0, atol=tol):  # refatm_same_selres
                raise ValueError("selres = selatm, but the sum over"
                                 " 'hist_atm[2]' ({}) is not one"
                                 .format(np.sum(hist_atm[2])))
            if np.any(hist_res[3] != hist_res[0]):
                # refres_diff_selres != refres_diff_selatm
                raise ValueError("selres = selatm, but 'hist_res[3]' !="
                                 " 'hist_res[0]'")
            if np.any(hist_res[4] != hist_res[1]):
                # refres_same_selres != refres_same_selatm
                raise ValueError("selres = selatm, but 'hist_res[4]' !="
                                 " 'hist_res[1]'")
            if not np.isclose(hist_par[0][1], 1, rtol=0, atol=tol):  # refatm_selres_pair
                raise ValueError("selres = selatm, but 'hist_par[0]'"
                                 " != [0, 1]")
            if not np.isclose(np.sum(hist_par[0]), 1, rtol=0, atol=tol):  # refatm_selres_pair
                raise ValueError("selres = selatm, but the sum over"
                                 " 'hist_par[0]' ({}) is not one"
                                 .format(np.sum(hist_par[0])))
            if np.any(hist_par[2] != hist_par[1]):
                # refres_selres_pair != refres_selatm_pair
                raise ValueError("selres = selatm, but 'hist_par[2]' !="
                                 " 'hist_par[1]'")
    
    if not np.isclose(av_atm[1]*av_par_bound[0], av_atm[0],
                      rtol=0, atol=tol):
        raise ValueError("The average selres coordination number of all"
                         " refatms ({}) times the average number of"
                         " 'bonds' between refatm-selres pairs ({})"
                         " differs from the average selatm coordination"
                         " number of all refatms ({})"
                         .format(av_atm[1], av_par_bound[0], av_atm[0]))
    if not np.isclose(av_atm_bound[1]*av_par_bound[0], av_atm_bound[0],
                      rtol=0, atol=tol):
        raise ValueError("The average selres coordination number of"
                         " bound refatms ({}) times the average number"
                         " of 'bonds' between refatm-selres pairs ({})"
                         " differs from the average selatm coordination"
                         " number of bound refatms ({})"
                         .format(av_atm_bound[1],
                                 av_par_bound[0],
                                 av_atm_bound[0]))
    if not np.isclose(av_res[0]*av_par_bound[1], av_res[2],
                      rtol=0, atol=tol):
        raise ValueError("The average selatm coordination number of all"
                         " refres ({}) times the average number of"
                         " 'bonds' between refres-selatm pairs ({})"
                         " differs from the average total selatm"
                         " coordination number of all refres ({})"
                         .format(av_res[0], av_par_bound[1], av_res[2]))
    if not np.isclose(av_res_bound[0]*av_par_bound[1], av_res_bound[2],
                      rtol=0, atol=tol):
        raise ValueError("The average selatm coordination number of"
                         " bound refres ({}) times the average number"
                         " of 'bonds' between refres-selatm pairs ({})"
                         " differs from the average total selatm"
                         " coordination number of bound refres ({})"
                         .format(av_res_bound[0],
                                 av_par_bound[1],
                                 av_res_bound[2]))
    if not np.isclose(av_res[3]*av_par_bound[2], av_res[2],
                      rtol=0, atol=tol):
        raise ValueError("The average selres coordination number of all"
                         " refres ({}) times the average number of"
                         " 'bonds' between refres-selres pairs ({})"
                         " differs from the average total selatm"
                         " coordination number of all refres ({})"
                         .format(av_res[3], av_par_bound[2], av_res[2]))
    if not np.isclose(av_res_bound[3]*av_par_bound[2], av_res_bound[2],
                      rtol=0, atol=tol):
        raise ValueError("The average selres coordination number of"
                         " bound refres ({}) times the average number"
                         " of 'bonds' between refres-selres pairs ({})"
                         " differs from the average total selatm"
                         " coordination number of bound refres ({})"
                         .format(av_res_bound[3],
                                 av_par_bound[2],
                                 av_res_bound[2]))
    print("Elapsed time:         {}".format(datetime.now()-timer))
    print("Current memory usage: {:.2f} MiB"
          .format(proc.memory_info().rss/2**20))
    
    print("\n")
    print("{} done".format(os.path.basename(sys.argv[0])))
    print("Totally elapsed time: {}".format(datetime.now()-timer_tot))
    print("CPU time:             {}"
          .format(timedelta(seconds=sum(proc.cpu_times()[:4]))))
    print("CPU usage:            {:.2f} %".format(proc.cpu_percent()))
    print("Current memory usage: {:.2f} MiB"
          .format(proc.memory_info().rss/2**20))
