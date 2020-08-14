#! /usr/bin/env python3
# -*- Coding: UTF-8 -*-

r"""
draw_orb_energy_level_chemdraw.py

version 2.2

use '--help', '-h' or '/?' as the only argument to print this document and exit.

Draw energy level of orbitals from Gaussian or ORCA output file.
Please set your ChemDraw style to "ACS Document 1996" before using.
This program has been tested for Gaussian 16, ORCA 4.2.1 and ChemDraw 19.

If there are expected to be more than one page, but only one page can be found
in ChemDraw, just try rebooting the entire ChemDraw.

usage mode 1: command argument(s) mode
    python draw_orb_energy_level_chemdraw.py inputName [lowerThreshold higherThreshold]
    inputName is the file path of a Gaussian/ORCA input file.
    lowerThreshold and higherThreshold are two thresholds for printing, in unit eV.
    Only energy levels between these two thresholds will be printed.
    If only inputName is provided, the default thresholds will be used.

usage mode 2: interactive mode
    python draw_orb_energy_level_chemdraw.py
    follow the hints.
    usage mode 2.1:
        input a blank line to open a GUI window to select the input file.
    usage mode 2.2:
        input the path of the input file directly.
    Then input two thresholds, seperated by ' ' or ',', or input a blank line to use the
    default value.

The defaule Thresholds are -50.0 eV and 50.0 eV.


updated log:
version 0.1: tested how to draw energy level with Chemdraw.
version 1.0: the iniial version, can only be used for Gaussian Restricted wavefunction.
version 1.1: added interaction mode.
version 1.2: for Gaussian, ORCA. Restricted, Unrestricted, Restricted-Open.
version 1.3: added orbital index, dashed line for spliting alpha and beta, and for energy level 0.
version 1.4: can choose a range of printing.
version 2.0: rewrote most codes, more likely to be OOP instead of POP.
version 2.1: used some modules to make the code easier to be read.
version 2.2: added a GUI for opening the file.

"""

__version__ = 2.2

import os
from sys import argv
from collections import namedtuple
import re
import tkinter
import tkinter.filedialog as tkfd

root = tkinter.Tk()
root.withdraw() # hide Tk window

class Const(object):
    class ConstError(KeyError):
        pass
    def __setattr__(self, key, value):
        if key in self.__dict__.keys():
            raise self.ConstError("Cannot rebind const (%s)" % key)
        else:
            self.__dict__[key] = value

Position = namedtuple('Position', ['x', 'y'])

ClassifiedData = namedtuple('ClassfiedData', ['number', 'amount'])

class ClassifiableList(list):
    r"""
a list that has the method 'ClassifyData'.
"""
    def __init__(self, *pargs, **kwargs):
        r'''
    same as list
    '''
        super().__init__(*pargs, **kwargs)
        return
    def ClassifyData(self, classifyThreshold) -> ClassifiedData:
        r'''
    classify data according to 'classifyThreshold'.
    returns a 'ClassfiedData'.
    '''
        classified = ClassifiedData(number = list(), amount = list())
        for t in sorted(self):
            if ((len(classified.number) == 0) or
                (abs(t - classified.number[-1]) > classifyThreshold)):
                classified.number.append(t)
                classified.amount.append(1)
            else:
                classified.number[-1] = classified.number[-1] * classified.amount[-1] + t
                classified.amount[-1] += 1
                classified.number[-1] /= classified.amount[-1]
        return classified

class Orbital(object):
    def __init__(self, wfnType):
        r'''initialize the type of wavefunction.'''
        self.wfnType = wfnType
        return

# global environment
const = Const()
const.HartreeToeV: float = 27.211381581530137 # never change, it is a constant
itemId: int = 0 # for chemdraw

# variables you can change before executing
energyThreshold: float = 1E-3 # the threshold to decide whether degenerated or not
EnergyGapToGraphGap = 50. #  the energy difference will be converted to the y distance

# you should only change the y coordinate of originPos, or change nothing
# for the three lines below.
originPos : Position = Position(260, 80)
originPosA: Position = Position(130, originPos.y)
originPosB: Position = Position(390, originPos.y)

def ReadOrbitalFromOutFile(filename: str):
    global const
    # test whether this is a Gaussian output file or an ORCA output file.
    multiplicity = 0 # for orca, this variable is useless, so it is set to 0.
    # for Gaussian, multiplicity will be read.
    # all orbital energies are in unit eV.
    with open(filename) as fl:
        for l in fl:
            if 'O   R   C   A' in l:
                outType = 'ORCA'
                break
            if 'Gaussian(R)' in l:
                outType = 'Gaussian'
                fl.seek(0)
                for l in fl:
                    if 'Multiplicity =' in l:
                        multiplicity = int(l[l.index('Multiplicity =') + len('Multiplicity ='):])
                        break
                break
    # check the wavefunction type, R, U, or RO.
    with open(filename) as fl:
        if outType == 'Gaussian':
            for l in fl:
                if 'Alpha virt.' in l:
                    for l in fl:
                        if 'Beta virt.' in l:
                            wfnType = 'U'
                            break
                        if 'Condensed to atoms' in l:
                            wfnType = 'R'
                            if multiplicity > 1:
                                wfnType += 'O'
                            break
                    break
        elif outType == 'ORCA':
            for l in fl:
                if 'ORBITAL ENERGIES' in l:
                    fl.readline() # '-' * 16
                    l = fl.readline() # 'SPIN UP ORBITALS' or ''
                    if not l.isspace():
                        wfnType = 'U'
                        break
                    else:
                        wfnType = 'R'
                        fl.readline() # Title
                        for l in fl:
                            occuNumStr = l.strip().split()[1]
                            if occuNumStr == '0.0000':
                                break
                            if occuNumStr == '1.0000':
                                wfnType += 'O'
                                break
                        break            
    # read orbital energy information
    orb = Orbital(wfnType = wfnType)
    # set attributes
    orbAttrDict = {'R' : ('occ' , 'vir'), # occ for occupied, vir for virtural
                   'U' : ('aocc', 'bocc', 'avir', 'bvir'), # a for alpha, b for vir
                   'RO': ('docc', 'socc', 'nvir')# d for double-occupied, s for single-occupied,
                  }                              # n just for make a name difference.
    for attrib in orbAttrDict[orb.wfnType]:
        setattr(orb, attrib, ClassifiableList())
    # read orbital energy levels 
    with open(filename) as fl:
        if outType == 'Gaussian':
            ReadGauEne = lambda _: const.HartreeToeV * float(_)
            # read a string of energy in unit Hartree, 
            # then convert it to unit eV.
            for l in fl:
                if 'The electronic state is' in l: break
            if orb.wfnType == 'R':
                for l in fl:
                    if not ('eigenvalues' in l): break
                    if 'occ' in l:
                        orb.occ.extend(map(ReadGauEne, l.strip().split()[4:]))
                    elif 'vir' in l:
                        orb.vir.extend(map(ReadGauEne, l.strip().split()[4:]))
            elif orb.wfnType == 'U':
                for l in fl:
                    if not ('eigenvalues' in l): break
                    if 'Alpha' in l:
                        if 'occ' in l:
                            orb.aocc.extend(map(ReadGauEne, l.strip().split()[4:]))
                        elif 'vir' in l:
                            orb.avir.extend(map(ReadGauEne, l.strip().split()[4:]))
                    elif 'Beta' in l:
                        if 'occ' in l:
                            orb.bocc.extend(map(ReadGauEne, l.strip().split()[4:]))
                        elif 'vir' in l:
                            orb.bvir.extend(map(ReadGauEne, l.strip().split()[4:]))
            elif orb.wfnType == 'RO':
                occ = list() # double occupied as well as single occupied
                for l in fl:
                    if not ('eigenvalues' in l): break
                    if 'occ' in l:
                        occ.extend(map(ReadGauEne, l.strip().split()[4:]))
                    elif 'vir' in l:
                        orb.nvir.extend(map(ReadGauEne, l.strip().split()[4:]))
                orb.docc = ClassifiableList(occ[: - (multiplicity - 1)])
                orb.socc = ClassifiableList(occ[- (multiplicity - 1):])
                del(occ)
        elif outType == 'ORCA':
            for l in fl:
                if 'ORBITAL ENERGIES' in l: break
            fl.readline() # '-' * 16
            if orb.wfnType == 'R':
                fl.readline() # blank line
                fl.readline() # title
                for l in fl:
                    if 'Total SCF' in l: break
                    t = l.strip().split()
                    if t[1] == '2.0000':
                        orb.occ.append(float(t[3]))
                    elif t[1] == '0.0000':
                        orb.vir.append(float(t[3]))
            elif orb.wfnType == 'U':
                fl.readline() # 'SPIN UP ORBITALS'
                fl.readline() # title
                for l in fl:
                    if l.isspace(): break
                    t = l.strip().split()
                    if t[1] == '1.0000':
                        orb.aocc.append(float(t[3]))
                    elif t[1] == '0.0000':
                        orb.avir.append(float(t[3]))
                fl.readline() # 'SPIN DOWN ORBITALS'
                fl.readline() # title
                for l in fl:
                    if 'Total SCF' in l: break
                    t = l.strip().split()
                    if t[1] == '1.0000':
                        orb.bocc.append(float(t[3]))
                    elif t[1] == '0.0000':
                        orb.bvir.append(float(t[3]))
            elif wfnType == 'RO':
                fl.readline() # blank line
                fl.readline() # title
                for l in fl:
                    if 'Total SCF' in l: break
                    t = l.strip().split()
                    if t[1] == '2.0000':
                        orb.docc.append(float(t[3]))
                    elif t[1] == '1.0000':
                        orb.socc.append(float(t[3]))
                    elif t[1] == '0.0000':
                        orb.nvir.append(float(t[3]))
    return outType, orb

# below are functions and classes for drawing

class OrbitalDrawer(object):
    r"""
should only be used with "with".
"""
    def __init__(self, file):
        r'''
    only the file should be provided, should be opened as writable mode before.
    using 'with open(filename, "w") as f:
               with OrbitalDrawer(f) as drawer:
                   ...
          '
    is a good choice.
    '''
        self.file = file
        return

    def __enter__(self):
        r'''
    print the initial part, including xml version, CDXML begin, 
    colortable, fonttable, page begin, ...
    The file should be opened before.
    '''
        print('''<?xml version="1.0" encoding="UTF-8" ?>
<CDXML
 CreationProgram="ChemDraw"
 Name="%s"
>
    <colortable>
        <color r="1" g="1" b="1"/>
        <color r="0" g="0" b="0"/>
        <color r="1" g="0" b="0"/>
        <color r="1" g="1" b="0"/>
        <color r="0" g="1" b="0"/>
        <color r="0" g="1" b="1"/>
        <color r="0" g="0" b="1"/>
        <color r="1" g="0" b="1"/>
    </colortable>
    <fonttable>
        <font id="0" charset="iso-8859-1" name="Arial"/>
    </fonttable>
    <page>''' % self.file.name, file = self.file)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        r'''
    print the final part, including CDXML end and page end.
    The file should be opened before.
    '''
        print('''    </page>
</CDXML>

''', file = self.file)
        return

    def PrintLine(self, posx: float, posy: float) -> None:
        r'''
    print a bar line.
    The file should be opened before.
    '''
        global itemId
        itemId += 1
        print('''        <arrow
         id="%d"
         FillType="None"
         ArrowheadType="Solid"
         Head3D="%.1lf %.1lf 0"
         Tail3D="%.1lf %.1lf 0"
        />''' % (itemId, posx, posy, (posx + 20), posy), file = self.file)
        return

    def PrintUpArrow(self, posx: float, posy: float) -> None:
        r'''
    print a up arrow.
    The file should be opened before.
    '''
        global itemId
        itemId += 1
        print('''        <arrow
         id="%d"
         FillType="None"
         ArrowheadHead="Full"
         ArrowheadType="Solid"
         HeadSize="1000"
         ArrowheadCenterSize="800"
         ArrowheadWidth="200"
         Head3D="%.1lf %.1lf 0"
         Tail3D="%.1lf %.1lf 0"
        />''' % (itemId, posx, (posy - 15), posx, posy), file = self.file)
        return

    def PrintDownArrow(self, posx: float, posy: float) -> None:
        r'''
    print a down arrow.
    The file should be opened before.
    '''
        global itemId
        itemId += 1
        print('''        <arrow
         id="%d"
         FillType="None"
         ArrowheadHead="Full"
         ArrowheadType="Solid"
         HeadSize="1000"
         ArrowheadCenterSize="800"
         ArrowheadWidth="200"
         Head3D="%.1lf %.1lf 0"
         Tail3D="%.1lf %.1lf 0"
        />''' % (itemId, posx, posy, posx, (posy - 15)), file = self.file)
        return

    def PrintText(self, posx: float, posy: float, content: str, colorId: int = 0) -> None:
        r'''
    print text.
    The file should be opened before.
    '''
        global itemId
        itemId += 1
        print('''        <t
         id="%d"
         p="%.1lf %.1lf"
         LineHeight="auto"
        >
            <s font="0" color="%d" size="8">%s</s>
        </t>''' % (itemId, posx, posy, colorId, content), file = self.file)
        return

    def PrintDoubleOccupied(self, posx: float, posy: float, energy: float) -> None:
        r'''
    draw a double-occupied orbital.
    The file should be opened before.
    '''
        self.PrintLine(posx, posy)
        self.PrintUpArrow(posx + 6, posy - 5)
        self.PrintDownArrow(posx + 14, posy - 5)
        self.PrintText(posx - 5, posy + 10, '%7.2lf' % energy)
        return

    def PrintSingleAlphaOccupied(self, posx: float, posy: float, energy: float) -> None:
        r'''
    draw a single-occupied alpha orbital.
    The file should be opened before.
    '''
        self.PrintLine(posx, posy)
        self.PrintUpArrow(posx + 10, posy - 5)
        self.PrintText(posx - 5, posy + 10, '%7.2lf' % energy)
        return

    def PrintSingleBetaOccupied(self, posx: float, posy: float, energy: float) -> None:
        r'''
    draw a single-occupied beta orbital.
    The file should be opened before.
    '''
        self.PrintLine(posx, posy)
        self.PrintDownArrow(posx + 10, posy - 5)
        self.PrintText(posx - 5, posy + 10, '%7.2lf' % energy)
        return

    def PrintUnOccupied(self, posx: float, posy: float, energy: float) -> None:
        r'''
    draw an unoccupied orbital.
    The file should be opened before.
    '''
        self.PrintLine(posx, posy)
        self.PrintText(posx - 5, posy + 10, '%7.2lf' % energy)

    def PrintDashLine(self, posx: float, posy: float, length: float, ori: str, colorId: int = 6) -> None:
        r'''
    print a straight dashed line, horizon or vertical.
    The file should be opened before.
    The direction can be 'Right', 'Left', 'Up' or 'Down'.
    '''
        global itemId
        itemId += 1
        chgPosx, chgPosy = dict(R = (length, 0),
                                L = (-length, 0),
                                U = (0, -length),
                                D = (0, length))[ori[0].upper()]
        print('''        <arrow
         id="%d"
         color="%d"
         LineType="Dashed"
         FillType="None"
         ArrowheadType="Solid"
         Head3D="%.1lf %.1lf 0"
         Tail3D="%.1lf %.1lf 0"
        />''' % (itemId, colorId, posx, posy, (posx + chgPosx), (posy + chgPosy)), file = self.file)
        return

# below set details of printing

def GetPrintThreshold() -> tuple:
    global argv
    # To avoid the graph being too long, set two thresholds,
    # only energy between lowPrintThreshold and highPrintThreshold will be printed.
    lowPrtThre: float = -50.
    highPrtThre: float = 50.
    if len(argv) >= 4: # input file name, two thresholds are provided in command line
        lowPrtThre = float(argv[2])
        highPrtThre = float(argv[3])
    elif len(argv) == 3: # this should never happen
        raise ValueError('Provide two thresholds together and do not forget input file name.')
    elif len(argv) == 2: # only input file name provided, use default threshold
        pass
    else: # len(argv) == 1, interactive mode
        print('''
Now input a lower threshold and a higher threshold,
only energy between these two thresholds will be printed.
If a blank line is provided, the default will be used, which are
-50 eV and 50 eV.
Note that the value you input should in unit eV.
''')
        PrtThreCmd = input('Input: ')
        if (not PrtThreCmd.isspace()) and PrtThreCmd:
            lowPrtThre, highPrtThre = list(map(float, re.split(r'[\s\,]+', PrtThreCmd.strip())))
        else: # use default
            pass
    # to make sure the highPrtThre is not smaller than the lowPrThre.
    if lowPrtThre > highPrtThre:
        lowPrtThre, highPrtThre = highPrtThre, lowPrtThre
    if len(argv) == 1: # hint the threshold just input
        print('Only energy from %.1lf and %.1lf will be printed.' % (lowPrtThre, highPrtThre))
    return lowPrtThre, highPrtThre

MaxIn2 = lambda a, b: a if a >= b else b

# for drawing orbitals into chemdraw cdxml file.

def DrawR_Orbitals(orb) -> None:
    global argv, energyThreshold
    orbOcc = orb.occ.ClassifyData(energyThreshold)
    orbVir = orb.vir.ClassifyData(energyThreshold)
    if len(argv) == 1:
        print('This is a restricted wavefunction.')
        print('All energies are in unit eV.')
        print('')
        orbId = 0
        print('Occupied orbitals:')
        print('Energy (eV)       Orbital Index')
        for i in range(len(orbOcc.number)):
            print(' %7.2lf' % orbOcc.number[i], ' ' * 18, end = '')
            for j in range(orbOcc.amount[i]):
                orbId += 1
                print('%d' % orbId, end = ' ')
            print('')
        print('Virtual orbitals:')
        print('Energy (eV)       Orbital Index')
        for i in range(len(orbVir.number)):
            print(' %7.2lf' % orbVir.number[i], ' ' * 18, end = '')
            for j in range(orbVir.amount[i]):
                orbId += 1
                print('%d' % orbId, end = ' ')
            print('')
    lowPrtThre, highPrtThre = GetPrintThreshold()
    orbId = 0
    for i in range(len(orbOcc.number)):
        eneThis = orbOcc.number[i]
        startx = originPos.x - (orbOcc.amount[i] - 1) * 25 # * 50 / 2
        starty = originPos.y + (highPrtThre - eneThis) * EnergyGapToGraphGap
        for j in range(orbOcc.amount[i]):
            orbId += 1
            if (eneThis < lowPrtThre) or (eneThis > highPrtThre): continue
            drawer.PrintDoubleOccupied(startx + j * 50, starty, eneThis)
            drawer.PrintText(startx + j * 50 + 23, starty + 3, str(orbId), colorId = 9)
    for i in range(len(orbVir.number)):
        eneThis = orbVir.number[i]
        startx = originPos.x - (orbVir.amount[i] - 1) * 25 # * 50 / 2
        starty = originPos.y + (highPrtThre - eneThis) * EnergyGapToGraphGap
        for j in range(orbVir.amount[i]):
            orbId += 1
            if (eneThis < lowPrtThre) or (eneThis > highPrtThre): continue
            drawer.PrintUnOccupied(startx + j * 50, starty, eneThis)
            drawer.PrintText(startx + j * 50 + 23, starty + 3, str(orbId), colorId = 9)
    if (lowPrtThre < 0) and (highPrtThre > 0):
        drawer.PrintDashLine(10, originPos.y + highPrtThre * EnergyGapToGraphGap, 520, 'right')
    return

def DrawU_Orbitals(orb) -> None:
    global argv
    orbAOcc = orb.aocc.ClassifyData(energyThreshold)
    orbAVir = orb.avir.ClassifyData(energyThreshold)
    orbBOcc = orb.bocc.ClassifyData(energyThreshold)
    orbBVir = orb.bvir.ClassifyData(energyThreshold)
    if len(argv) == 1:
        print('This is an unrestricted wavefunction.')
        print('All energies are in unit eV.')
        print('')
        orbId = 0
        print('Alpha occupied orbitals:')
        print('Energy (eV)       Orbital Index')
        for i in range(len(orbAOcc.number)):
            print(' %7.2lf' % orbAOcc.number[i], ' ' * 18, end = '')
            for j in range(orbAOcc.amount[i]):
                orbId += 1
                print('%d' % orbId, end = ' ')
            print('')
        print('Alpha virtual orbitals:')
        print('Energy (eV)       Orbital Index')
        for i in range(len(orbAVir.number)):
            print(' %7.2lf' % orbAVir.number[i], ' ' * 18, end = '')
            for j in range(orbAVir.amount[i]):
                orbId += 1
                print('%d' % orbId, end = ' ')
            print('')
        orbId = 0
        print('Beta occupied orbitals:')
        print('Energy (eV)       Orbital Index')
        for i in range(len(orbBOcc.number)):
            print(' %7.2lf' % orbBOcc.number[i], ' ' * 18, end = '')
            for j in range(orbBOcc.amount[i]):
                orbId += 1
                print('%d' % orbId, end = ' ')
            print('')
        print('Beta virtual orbitals:')
        print('Energy (eV)       Orbital Index')
        for i in range(len(orbBVir.number)):
            print(' %7.2lf' % orbBVir.number[i], ' ' * 18, end = '')
            for j in range(orbBVir.amount[i]):
                orbId += 1
                print('%d' % orbId, end = ' ')
            print('')
    lowPrtThre, highPrtThre = GetPrintThreshold()
    orbId = 0
    for i in range(len(orbAOcc.number)):
        eneThis = orbAOcc.number[i]
        startx = originPosA.x - (orbAOcc.amount[i] - 1) * 25 # * 50 / 2
        starty = originPosA.y + (highPrtThre - eneThis) * EnergyGapToGraphGap
        for j in range(orbAOcc.amount[i]):
            orbId += 1
            if (eneThis < lowPrtThre) or (eneThis > highPrtThre): continue
            drawer.PrintSingleAlphaOccupied(startx + j * 50, starty, eneThis)
            drawer.PrintText(startx + j * 50 + 23, starty + 3, str(orbId), colorId = 9)
    for i in range(len(orbAVir.number)):
        eneThis = orbAVir.number[i]
        startx = originPosA.x - (orbAVir.amount[i] - 1) * 25 # * 50 / 2
        starty = originPosA.y + (highPrtThre - eneThis) * EnergyGapToGraphGap
        for j in range(orbAVir.amount[i]):
            orbId += 1
            if (eneThis < lowPrtThre) or (eneThis > highPrtThre): continue
            drawer.PrintUnOccupied(startx + j * 50, starty, eneThis)
            drawer.PrintText(startx + j * 50 + 23, starty + 3, str(orbId), colorId = 9)
    orbId = 0
    for i in range(len(orbBOcc.number)):
        eneThis = orbBOcc.number[i]
        startx = originPosB.x - (orbBOcc.amount[i] - 1) * 25 # * 50 / 2
        starty = originPosB.y + (highPrtThre - eneThis) * EnergyGapToGraphGap
        for j in range(orbBOcc.amount[i]):
            orbId += 1
            if (eneThis < lowPrtThre) or (eneThis > highPrtThre): continue
            drawer.PrintSingleBetaOccupied(startx + j * 50, starty, eneThis)
            drawer.PrintText(startx + j * 50 + 23, starty + 3, str(orbId), colorId = 9)
    for i in range(len(orbBVir.number)):
        eneThis = orbBVir.number[i]
        startx = originPosB.x - (orbBVir.amount[i] - 1) * 25 # * 50 / 2
        starty = originPosB.y + (highPrtThre - eneThis) * EnergyGapToGraphGap
        for j in range(orbBVir.amount[i]):
            orbId += 1
            if (eneThis < lowPrtThre) or (eneThis > highPrtThre): continue
            drawer.PrintUnOccupied(startx + j * 50, starty, eneThis)
            drawer.PrintText(startx + j * 50 + 23, starty + 3, str(orbId), colorId = 9)
    drawer.PrintDashLine(270, 10,
                         2 * originPos.y + (highPrtThre - lowPrtThre) * EnergyGapToGraphGap - 10,
                         'Down', colorId = 0)
    if (lowPrtThre < 0) and (highPrtThre > 0):
        drawer.PrintDashLine(10, originPos.y + highPrtThre * EnergyGapToGraphGap, 520, 'right')
    return

def DrawRO_Orbitals(orb) -> None:
    global argv
    orbDOcc = orb.docc.ClassifyData(energyThreshold)
    orbSOcc = orb.socc.ClassifyData(energyThreshold)
    orbNVir = orb.nvir.ClassifyData(energyThreshold)
    if len(argv) == 1:
        print('This is a restricted open wavefunction.')
        print('All energies are in unit eV.')
        print('')
        orbId = 0
        print('Double occupied orbitals:')
        print('Energy (eV)       Orbital Index')
        for i in range(len(orbDOcc.number)):
            print(' %7.2lf' % orbDOcc.number[i], ' ' * 18, end = '')
            for j in range(orbDOcc.amount[i]):
                orbId += 1
                print('%d' % orbId, end = ' ')
            print('')
        print('Single occupied orbitals:')
        print('Energy (eV)       Orbital Index')
        for i in range(len(orbSOcc.number)):
            print(' %7.2lf' % orbSOcc.number[i], ' ' * 18, end = '')
            for j in range(orbSOcc.amount[i]):
                orbId += 1
                print('%d' % orbId, end = ' ')
            print('')
        print('Virtual orbitals:')
        print('Energy (eV)       Orbital Index')
        for i in range(len(orbNVir.number)):
            print(' %7.2lf' % orbNVir.number[i], ' ' * 18, end = '')
            for j in range(orbNVir.amount[i]):
                orbId += 1
                print('%d' % orbId, end = ' ')
            print('')
    lowPrtThre, highPrtThre = GetPrintThreshold()
    orbId = 0
    for i in range(len(orbDOcc.number)):
        eneThis = orbDOcc.number[i]
        startx = originPos.x - (orbDOcc.amount[i] - 1) * 25 # * 50 / 2
        starty = originPos.y + (highPrtThre - eneThis) * EnergyGapToGraphGap
        for j in range(orbDOcc.amount[i]):
            orbId += 1
            if (eneThis < lowPrtThre) or (eneThis > highPrtThre): continue
            drawer.PrintDoubleOccupied(startx + j * 50, starty, eneThis)
            drawer.PrintText(startx + j * 50 + 23, starty + 3, str(orbId), colorId = 9)
    for i in range(len(orbSOcc.number)):
        eneThis = orbSOcc.number[i]
        startx = originPos.x - (orbSOcc.amount[i] - 1) * 25 # * 50 / 2
        starty = originPos.y + (highPrtThre - eneThis) * EnergyGapToGraphGap
        for j in range(orbSOcc.amount[i]):
            orbId += 1
            if (eneThis < lowPrtThre) or (eneThis > highPrtThre): continue
            drawer.PrintSingleAlphaOccupied(startx + j * 50, starty, eneThis)
            drawer.PrintText(startx + j * 50 + 23, starty + 3, str(orbId), colorId = 9)
    for i in range(len(orbNVir.number)):
        eneThis = orbNVir.number[i]
        startx = originPos.x - (orbNVir.amount[i] - 1) * 25 # * 50 / 2
        starty = originPos.y + (highPrtThre - eneThis) * EnergyGapToGraphGap
        for j in range(orbNVir.amount[i]):
            orbId += 1
            if (eneThis < lowPrtThre) or (eneThis > highPrtThre): continue
            drawer.PrintUnOccupied(startx + j * 50, starty, eneThis)
            drawer.PrintText(startx + j * 50 + 23, starty + 3, str(orbId), colorId = 9)
    if (lowPrtThre < 0) and (highPrtThre > 0):
        drawer.PrintDashLine(10, originPos.y + highPrtThre * EnergyGapToGraphGap, 520, 'right')
    return

drawTypeDict = {'R': DrawR_Orbitals, 'U': DrawU_Orbitals, 'RO': DrawRO_Orbitals}

## The main part ##

# get input file name and output file name
if len(argv) > 1: # command mode
    if argv[1] in ('--help', '-h', '/?'): # help only
        print(__doc__)
        print('Exiting normally...')
        exit()
    iname = argv[1]
else: # interaction mode
    print('''This program reads output file of a(n) Gaussian/ORCA output file,
then generates a ChemDraw cdxml file to show the graph of orbital energy levels.
Only single-reference methods can be used.
Please set your ChemDraw template to 'ACS 1996 Documents'.
''')
    print('Directly press <Enter> will open a GUI to choose the file.')
    print('or input name of a Gaussian/ORCA output file below:')
    iname = input()
    if (not iname) or iname.isspace(): # blank line, open a GUI
        iname = tkfd.askopenfilename(title = 'Choose a Gaussian/ORCA output file',
                                     filetypes = [('Gaussian output file', '.out'),
                                                  (    'ORCA output file', '.out')])
    else: # file name input, check the extension name.
        if os.path.splitext(iname)[1] != '.out':
            raise NotImplementedError('Only .out file can be read!')
oname = os.path.splitext(iname)[0] + '_orbital_energy_level' + '.cdxml'

# test if the input file can be opened
with open(iname) as f:
    pass
# obtain orbitals energy information
outType, orb = ReadOrbitalFromOutFile(iname)

if len(argv) == 1:
    print('Using file:', iname)
    print('Loading, please wait...')
    print('This is an output file of %s.' % outType)

with open(oname, 'w') as ofile:
    with OrbitalDrawer(ofile) as drawer:  
        drawTypeDict[orb.wfnType](orb)

if len(argv) == 1: print('Everything is done. Check \"%s\".' % oname)

