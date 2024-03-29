"""
Script to manage SVJProduction tarball making
"""
from __future__ import print_function
import qondor, seutils
import os.path as osp, os, glob, argparse, time, shutil

THISDIR = osp.abspath(osp.dirname(__file__))
TARBALLDIR = osp.join(THISDIR, 'tarballs')
STAGEOUTDIR = 'root://cmseos.fnal.gov//store/user/lpcsusyhad/SVJ2017/boosted/svjproduction-tarballs'

CMSSW_VERSION = {
    '2016' : {
        'gen' : 'CMSSW_7_1_44',
        'miniaod' : 'CMSSW_8_0_28'
        },
    '2017' : {
        'gen' : 'CMSSW_9_3_14',
        'miniaod' : 'CMSSW_9_4_10'
        },
    '2018' : {
        'gen' : 'CMSSW_10_2_21',
        'miniaod' : 'CMSSW_10_2_21'
        },
    '2018UL' : {
        'gen' : 'CMSSW_10_6_29_patch1',
        'miniaod' : 'CMSSW_10_6_29_patch1'
        },
    'treemaker' : {
        'treemaker' : 'CMSSW_10_2_21'
        }
    }

YEARS = [ '2016', '2017', '2018', '2018UL' ]
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
    if not steps is None and '*' in steps: steps = STEPS[:]
    for year in years:
        if year == 'treemaker':
            yield 'treemaker', 'treemaker'
            continue
        for step in steps:
            yield year, step

SLVERSION = None
def slversion():
    global SLVERSION
    if SLVERSION is None:
        # Prefer to read from /etc/redhat-release; os.uname does not work in singularity image
        try:
            if osp.isfile('/etc/redhat-release'):
                with open('/etc/redhat-release', 'r') as f:
                    SLVERSION = 'el' + f.read().strip().split('release',1)[1].strip()[0]
        except:
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

def treemakerdir():
    return osp.join(cmsswsrcdir('treemaker', 'treemaker'), 'TreeMaker')

def packagedir(year, step=None):
    return treemakerdir() if year == 'treemaker' else svjproductiondir(year, step)

def setup(year, step):
    if not DRYMODE and not osp.isdir(yeardir(year)): os.makedirs(yeardir(year))
    if year == 'treemaker':
        qondor.utils.run_multiple_commands([
            'cd {0}'.format(yeardir(year)),
            'wget https://raw.githubusercontent.com/TreeMaker/TreeMaker/Run2_2017/setup.sh',
            'chmod +x setup.sh',
            ])
        if slversion() == 'el6':
            duckpunch_el6_treemaker_setup(osp.join(yeardir('treemaker'), 'setup.sh'))
        qondor.utils.run_multiple_commands([
            'cd {0}'.format(yeardir(year)),
            './setup.sh -f boostedsvj -b boosted_rebased',
            ])
    else:
        if 'UL' in year:
            setuppy = 'https://raw.githubusercontent.com/cms-svj/SVJProduction/master/setup.sh'
            fork = ''
        else:
            setuppy = 'https://raw.githubusercontent.com/kpedro88/SVJProduction/master/setup.sh'
            fork = '-f boostedsvj'
        cmds = [
            'cd {0}'.format(yeardir(year)),
            'wget {0} -O setup.sh'.format(setuppy),
            'chmod +x setup.sh',
            './setup.sh -c {0} {1} -s ssh'.format(CMSSW_VERSION[year][step], fork),
            ]
        qondor.utils.run_multiple_commands(cmds)

def duckpunch_el6_treemaker_setup(setup_file):
    """
    Duck-punches SLC_VERSION="slc6" in the setup script
    """
    print('WARNING: Duck-punching {0}'.format(setup_file))
    with open(setup_file, 'r') as f:
        setup = f.read()
    # Insert
    target_line = 'export SCRAM_ARCH=${SLC_VERSION}_amd64_${GCC_VERSION}'
    setup = setup.replace(
        target_line,
        'export SLC_VERSION="slc6"\n' + target_line
        )
    with open(setup_file, 'w') as f:
        f.write(setup)

def pull(year, step):
    '''Pulls latest SVJ/Production from git and recompiles'''
    cmds = [
        'export VO_CMS_SW_DIR=/cvmfs/cms.cern.ch/',
        'source /cvmfs/cms.cern.ch/cmsset_default.sh',
        'cd {0}'.format(cmsswsrcdir(year, step)),
        'eval \'scram runtime -sh\'',
        'cd {0}'.format(packagedir(year, step)),
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
            'cd {0}'.format(packagedir(year, step)),
            'git rev-parse --short HEAD'
            ])[0]
    if year == 'treemaker':
        tag = '_'.join([commitid, slversion(), 'treemaker', time.strftime('%b%d')])
    else:
        tag = '_'.join([commitid, slversion(), step, year, time.strftime('%b%d')])
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

def status(year, step=None):
    pdir = packagedir(year, step)
    if not osp.isdir(pdir):
        status_text = 'Not setup: {} {}'.format(year, step)
    else:
        last_commit = qondor.utils.run_multiple_commands([
            'cd {}'.format(pdir),
            'git rev-parse --abbrev-ref HEAD',
            'git log -n 1'
            ])
        status_text = (
            qondor.colored('\n' + pdir + ':', 'yellow')
            + '\n  ' + '\n  '.join(last_commit)
            )
    print(status_text)
    return status_text

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'action', type=str, choices=['setup', 'pull', 'tarball', 'stageout', 'status'],
        help=(
            'setup: Sets up a CMSSW environment; '
            'pull: Updates an existing CMSSW environment; '
            'tarball: Makes a tarball out of an existing CMSSW environment; '
            'stageout: Copies all created tarballs to the storage element (at {0}) '
            '(year and step arguments are ignored)'
            .format(STAGEOUTDIR)
            )
        )
    parser.add_argument(
        'year', type=str, nargs='?', choices=[str(y) for y in YEARS] + ['treemaker', '*'],
        help='Specify which year (each year may have different CMSSW versions)'
        )
    parser.add_argument(
        'step', type=str, nargs='?', choices=STEPS + ['*'],
        help='Specify which step (different steps may have different CMSSW versions)'
        )
    parser.add_argument(
        '-o', '--out', type=str,
        help='Path to where CMSSW should be set up (default is where this script is)'
        )
    parser.add_argument(
        '-d', '--dry', action='store_true',
        help='Only prints what would be done, but does not run anything'
        )
    args = parser.parse_args()

    if args.out:
        global THISDIR
        THISDIR = osp.abspath(args.out)
        qondor.logger.info('Working directory: %s', THISDIR)

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
        elif args.action == 'status':
            status(year, step)



if __name__ == '__main__':
    main()