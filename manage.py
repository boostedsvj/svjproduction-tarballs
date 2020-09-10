"""
Script to manage SVJProduction tarball making
"""

import qondor, seutils
import os.path as osp, os, glob, argparse, time, shutil

THISDIR = osp.abspath(osp.dirname(__file__))
TARBALLDIR = osp.join(THISDIR, 'tarballs')
STAGEOUTDIR = 'root://cmseos.fnal.gov//store/user/lpcsusyhad/SVJ2017/boosted/svjproduction-tarballs'

CMSSW_VERSION = {
    2016 : {
        'gen' : 'CMSSW_7_1_44',
        'miniaod' : 'CMSSW_8_0_28'
        },
    2017 : {
        'gen' : 'CMSSW_9_3_14',
        'miniaod' : 'CMSSW_9_4_10'
        },
    2018 : {
        'gen' : 'CMSSW_10_2_21',
        'miniaod' : 'CMSSW_10_2_21'
        }
    }

YEARS = [ 2016, 2017, 2018 ]
STEPS = [ 'gen', 'miniaod' ]


DRYMODE = False
def drymode(flag=True):
    global DRYMODE
    DRYMODE = flag
    qondor.drymode(flag)
    seutils.drymode(flag)

def iter_years_steps(years, steps):
    if qondor.utils.is_string(years): years = [years]
    if qondor.utils.is_string(steps): steps = [steps]
    if '*' in years: years = YEARS[:]
    if '*' in steps: steps = STEPS[:]
    for year in years:
        for step in steps:
            yield int(year), step

SLVERSION = None
def slversion():
    global SLVERSION
    if SLVERSION is None:
        SLVERSION = 'el7' if 'el7' in os.uname()[2] else 'el6'
    return SLVERSION

def yeardir(year):
    return osp.join(THISDIR, str(year) + '_' + slversion())

def cmsswdir(year, step):
    return osp.join(yeardir(year), CMSSW_VERSION[year][step])

def cmsswsrcdir(year, step):
    return osp.join(cmsswdir(year, step), 'src')

def svjproductiondir(year, step):
    return osp.join(cmsswsrcdir(year, step), 'SVJ/Production')

def setup(year, step):
    if not DRYMODE and not osp.isdir(yeardir(year)): os.makedirs(yeardir(year))
    cmds = [
        'cd {0}'.format(yeardir(year)),
        'wget https://raw.githubusercontent.com/kpedro88/SVJProduction/master/setup.sh -O setup.sh',
        'chmod +x setup.sh',
        './setup.sh -c {0} -f boostedsvj -s ssh'.format(CMSSW_VERSION[year][step]),
        ]
    qondor.utils.run_multiple_commands(cmds)

def pull(year, step):
    '''Pulls latest SVJ/Production from git and recompiles'''
    cmds = [
        'export VO_CMS_SW_DIR=/cvmfs/cms.cern.ch/',
        'source /cvmfs/cms.cern.ch/cmsset_default.sh',
        'cd {0}'.format(cmsswsrcdir(year, step)),
        'eval \'scram runtime -sh\'',
        'cd {0}'.format(svjproductiondir(year, step)),
        'git pull',
        'cd {0}'.format(cmsswsrcdir(year, step)),
        'scram b -j8',
        ]
    qondor.utils.run_multiple_commands(cmds)

def tarball_tag(year, step):
    if DRYMODE:
        commitid = '000000'
    else:
        commitid = qondor.utils.run_multiple_commands([
            'cd {0}'.format(svjproductiondir(year, step)),
            'git rev-parse --short HEAD'
            ])[0]
    tag = '{0}_{1}_{2}_{3}_{4}'.format(
        commitid, slversion(), step, year, time.strftime('%b%d')
        )
    return tag

def make_tarball(year, step):
    cmssw = qondor.CMSSW(cmsswsrcdir(year, step))
    if not osp.isdir(TARBALLDIR): os.makedirs(TARBALLDIR)
    tarball = cmssw.make_tarball(outdir=TARBALLDIR, tag=tarball_tag(year, step))
    if DRYMODE: tarball = 'CMSSW_X_Y_Z_{0}.tar.gz'.format(tarball_tag(year, step))
    # Also update 'latest'
    dst = osp.basename(tarball).split('_')
    dst[4] = 'latest'
     # Get rid of the date string for latest
    dst.pop(-1)
    dst[-1] += '.tar.gz'
    dst = '_'.join(dst)
    dst = osp.join(osp.dirname(tarball), dst)
    qondor.logger.info('Updating %s -> %s', tarball, dst)
    if not DRYMODE: shutil.copyfile(tarball, dst)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', type=str, choices=['setup', 'pull', 'tarball', 'stageout'], help='')
    parser.add_argument('year', type=str, nargs='?', choices=[str(y) for y in YEARS] + ['*'], help='')
    parser.add_argument('step', type=str, nargs='?', choices=STEPS + ['*'], help='')
    parser.add_argument('-d', '--dry', action='store_true', help='')
    args = parser.parse_args()

    if args.dry: drymode()

    if args.action == 'stageout':
        for tarball in glob.glob(osp.join(TARBALLDIR, '*.tar.gz')):
            dst = osp.join(STAGEOUTDIR, osp.basename(tarball))
            force = ('latest' in dst)
            if not force and seutils.isfile(dst):
                qondor.logger.info('%s already exists', dst)
            else:
                qondor.logger.info('Staging out %s --> %s', tarball, dst)
                seutils.cp(tarball, STAGEOUTDIR, force=force)
        return

    for year, step in iter_years_steps(args.year, args.step):
        if args.action == 'setup':
            setup(year, step)
        elif args.action == 'pull':
            pull(year, step)
        elif args.action == 'tarball':
            make_tarball(year, step)



if __name__ == '__main__':
    main()