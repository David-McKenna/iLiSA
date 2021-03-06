#!/usr/bin/env python

import sys
import os
import numpy
import datetime
import argparse
import ilisa.antennameta.antennafieldlib as antennafieldlib
import ilisa.antennameta.calibrationtables as calibrationtables
import ilisa.observations.dataIO as dataIO
import ilisa.observations.imaging as imaging
import ilisa.observations.stationcontrol as stationcontrol
import ilisa.observations.observing as observing


def main(accrunfolder, desiredsrc):
    """Convert the ACC folder into a hdf or numpy file.

    The output file will be created in the current working path.

    Parameters
    ----------
    accrunfolder : str
        Path to the folder that contains a set of temporally contiguous ACC files.

    stnid : str
        Station id. e.g. SE607.
    """
    accffobj = dataIO.CVCfiles(accrunfolder)
    obsfolderinfo = accffobj.getobsfolderinfo()
    obsdate = obsfolderinfo['datetime']
    rcumode = obsfolderinfo['rcumode']
    calsrc  = obsfolderinfo['calsrc']
    dur = obsfolderinfo['duration']
    stnid = obsfolderinfo['stnid']
    if calsrc == None and desiredsrc == None:
        raise ValueError, "No calibration source specified"
    elif int(rcumode) == 3 and desiredsrc is not None:
        calsrc = desiredsrc
    elif desiredsrc != calsrc:
        print("Warning: calibration source {} is not the desired one {}.".format(calsrc,desiredsrc))
    pntstr = observing.stdPointings(calsrc)
    pointing = pntstr.split(',')
    bandarr = stationcontrol.rcumode2antset(rcumode).split("_")[0]
    stnPos, stnRot, antpos, stnIntilePos = antennafieldlib.getArrayBandParams(stnid, bandarr)
    freqs = stationcontrol.rcumode2sbfreqs(rcumode)
    accfolderdatestr = obsdate.strftime("%Y%m%d") + "T120000" # FIX put appropriate time
    (nrant, comp) = antpos.shape
    ACCfiles = accffobj.filenames
    nrACCfiles = len(ACCfiles)
    (caltab, ctheader) = calibrationtables.getcaltab(rcumode, stnid, accfolderdatestr)

    sb = None
    if sb == None:
        (bstXX, bstXY, bstYY) = (
             numpy.zeros((nrACCfiles, stationcontrol.TotNrOfsb)),
             numpy.zeros((nrACCfiles, stationcontrol.TotNrOfsb), dtype=complex),
             numpy.zeros((nrACCfiles, stationcontrol.TotNrOfsb)))
    else:
        (bstXX, bstXY, bstYY) = (numpy.zeros((nrACCfiles, )),
                                        numpy.zeros((nrACCfiles, ), dtype=complex),
                                        numpy.zeros((nrACCfiles, )))
    filestarttimes = numpy.zeros((nrACCfiles,), dtype='datetime64[s]')

    for tidx, ACCfile in enumerate(ACCfiles):
        accunc = accffobj.getdata(tidx)
        sbobstimes = accffobj.samptimes[tidx]
        filestarttimes[tidx] = numpy.datetime64(sbobstimes[0])
        if tidx == 0:
            calrunstarttime = sbobstimes[0]
        else:
            ftd = numpy.asscalar((filestarttimes[tidx]-filestarttimes[tidx-1]).astype('int'))
            if ftd != 519:
                print("Time delta between ACC files is {}s.".format(ftd))
                raise RuntimeError("""Time between ACC files nr {}-{} not the \
                                   nominal 519s.""".format(tidx,tidx-1))
        # Calibrate
        acc = calibrationtables.calibrateACCwithtab(accunc, caltab)
        accpol = dataIO.cvc2cvpol(acc)
        sys.stdout.write('({}/{})\n'.format(tidx+1, nrACCfiles))
        if sb == None:
           (bstXX[tidx,:], bstXY[tidx,:], bstYY[tidx,:]
            ) = imaging.accpol2bst(accpol, sbobstimes, freqs,
                                  stnPos, antpos, pointing)
        else:
            (bstXX[tidx], bstXY[tidx], bstYY[tidx]
            ) = imaging.xst2bst(accpol[:,:,sb,...].squeeze(), sbobstimes[sb], freqs[sb],
                                stnPos, antpos, pointing)
    calrunendtime = sbobstimes[-1]
    ACCsbsampleduration = datetime.timedelta(seconds=1)
    calrunduration = calrunendtime - calrunstarttime + ACCsbsampleduration
    acc2bstname = dataIO.saveacc2bst((bstXX, bstXY, bstYY), filestarttimes,
                                     calrunstarttime, calrunduration, rcumode,
                                     calsrc, ctheader['Calibration'], stnid)
    print("Created file: {}".format(acc2bstname))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("accrunfolder")
    #parser.add_argument("stnid",type=str)
    parser.add_argument("desiredsrc", type=str, nargs='?', default=None)
    args = parser.parse_args()
    main(args.accrunfolder, args.desiredsrc)
