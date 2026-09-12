# BGU CIS 2024 Version HPC Cluster — User Guide

*Version date: 22/03/2026*

---

## Abstract

BGU ISE, DT and CS departments have a new (2024) Slurm cluster (HPC) that handles both GPU tasks and CPU tasks. Slurm is a job scheduler and resource manager used in most of the greatest super computers. The cluster consists of a manager node (also called master node) and several compute nodes.

**Architecture:** users SSH to a Login Node (`slurm.bgu.ac.il`), which routes to a Manager/Master Node. The manager dispatches jobs to GPU Compute Nodes or CPU Compute Nodes, all sharing a Shared Storage backend. Anaconda and Apache Spark are available.

> **The manager node is a shared resource used for launching, monitoring, and controlling jobs and should NEVER be used for computational purposes.**

- The compute nodes are powerful Linux servers, some of which are installed with GPUs.
- The user connects, by SSH, to the manager node and submits jobs that are executed by a compute node.
- A job is allocation of compute resources such as RAM memory, CPU cores, GPU, etc. for a limited time. A job may consist of job steps which are tasks within a job.
- In the following pages, *italic* writing is reserved for Slurm CLI commands.

---

## Use

- Make sure you got admission to the cluster by your IT team.
- SSH to the Login Node: `slurm.bgu.ac.il`
- Use your BGU user name and password to login. The default path is your home directory on the storage.
- **Python users:** create your virtual environment (Conda Create Environment) on the manager node.
- If you copy files to your home directory, don't forget about file permissions. E.g. for files that need execution permissions: `chmod +x <path to file>`
- Remember that the cluster is a **shared** resource. Users are trusted to act with responsibility — release unused allocated resources (with `scancel`), do not allocate more than needed, erase unused files and datasets. Release resources even if you are taking a few hours break from interactively using them.
- Anaconda3 is already installed on the cluster. **Do not install it!**
- Should you need `tensorflow-gpu`, do **not** use `pip install`. Use: `conda install -c anaconda tensorflow-gpu`
- If you are clueless about Linux/Conda/etc., use the Step by Step Guide for First Use, or the Moodle video tutorials.
- Moodle course: `HPC הדרכת קלסטר` at <https://moodle.bgu.ac.il/moodle/course/view.php?id=60163> — registration password `cluster20252`.

---

## Submitting a Job

Non-interactive job:

```bash
sbatch <your batch file name>
```

> **Conda users:** make sure you submit the job while the virtual environment is **deactivated** in the CLI (`conda deactivate`)!

For interactive jobs see [Interactive vs Non-Interactive Use](#interactive-vs-non-interactive-use).

### Batch File

Example located at `/storage/example.sbatch`:

```bash
#!/bin/bash
### sbatch config parameters must start with #SBATCH and must precede any other command. To ignore, prefix with another # — like ##SBATCH

#SBATCH --partition main                    ### partition name. Use 'main' unless QoS is required. QoS partitions: 'rtx3090' 'rtx2080' 'gtx1080'
#SBATCH --time 0-10:30:00                   ### time limit (must be ≤ partition time limit, 7 days). Format: D-H:MM:SS
#SBATCH --job-name my_job                   ### job name
#SBATCH --output my_job-id-%J.out           ### output log file. %J is the job number
#SBATCH --mail-user=user@post.bgu.ac.il     ### email for status notifications
#SBATCH --mail-type=BEGIN,END,FAIL          ### ALL,BEGIN,END,FAIL,REQUEU,NONE
#SBATCH --gpus=0                            ### number of GPUs. e.g. --gpus=gtx_1080:1, rtx_2080, rtx_3090. >1 requires IT permission.
##SBATCH --tasks=1                          ### 1 process. >1 only for MPI / multi-program with srun.

### Print some data to output file ###
echo "SLURM_JOBID"=$SLURM_JOBID
echo "SLURM_JOB_NODELIST"=$SLURM_JOB_NODELIST

### Start your code below ####
module load anaconda                        ### load anaconda module
source activate my_env                      ### activate conda env
python mycode.py my_arg
```

> When asking IT for support: include your **username**, **job id**, the **sbatch file** and the **output file** path/name.

---

## Allocating Resources

Resources are expensive and in high demand — use just **1 GPU per job**.

- Use the **minimum possible RAM**. If your code uses 30G, do NOT ask for 50G. To check post-mortem RAM use: `sacct -j <jobid> --format=JobName,MaxRSS`.
- You can only load ~11G to most of the GPUs and 24G to the advanced ones. **Do not allocate more than 60G!**
- **4–6 CPUs** are sufficient to serve a GPU. You should NOT set that value when allocating a GPU — the system handles it.
- If your job does not require a GPU, submit it to the CPU cluster.

---

## Interactive vs Non-Interactive Use

There are two ways to work with the cluster:

- **Non-interactive** (fire-and-forget): the user specifies the code; it runs on a compute node without user interaction. Terminal output is redirected to a file.
- **Interactive**: SSH session must remain open. Once it closes, the job cannot be renewed. Used for Jupyter notebooks or IDEs (PyCharm, VS Code).

To connect to a specific job's environment variables on a compute node:

```bash
srun --jobid=<your-jobid> --pty bash
```

Launch interactive job with defaults:

```bash
sinteractive
```

Help: `sinteractive --help`. 5-hour GPU job: `sinteractive --time 0-5:00:00 --gpu 1`. Course users: `sinteractive --qos course --part course --gpu 1`.

> **Do not forget to cancel the job when done:** `scancel <job_id>`

⚠️ Multiple simultaneous interactive jobs may land on the same compute node — see FAQ entry "simultaneous interactive jobs get the same compute node".

---

## Information about the compute nodes

```bash
sinfo                # cluster information
sinfo -Nel           # NODELIST = node name; S:C:T = sockets:cores:threads
```

## List of My Currently Running Jobs

```bash
squeue --me
```

## Cancel Jobs

```bash
scancel <job id>
scancel --name <job name>
```

### Cancel All Pending Jobs for a Specific User

```bash
scancel -t PENDING -u <user name>
```

## Running Job Information

```bash
sstat -j <job_id> --format=MaxRSS,MaxVMSize     # consumed memory
scontrol show job <job_id>
```

## Complete Job Information

```bash
sacct -j <jobid>
sacct -j <jobid> --format=JobName,MaxRSS,AllocTRES,State,Elapsed,Start,ExitCode,DerivedExitcode,Comment
```

`MaxRSS` is the maximum memory the job needed.

## Resources Usage

```bash
sres
```

Use it to make up your mind about which resources to use, when the cluster is near full capacity.

---

# Advanced Topics

You may also Run Jupyter Lab in Udocker.

## Jupyter Lab

### Installation

In your conda environment:

```bash
conda install jupyterlab
```

### Make the Conda Environment Available in Notebook's Interface

Activate your Jupyter-installed environment, then:

```bash
python -m ipykernel install --user --name <conda environment> --display-name "<env name to show in web browser>"
```

Example:

```bash
python -m ipykernel install --user --name my_env --display-name "my best env"
```

**Don't forget** to choose the right kernel inside the notebook.

### Launch Jupyter Lab

```bash
sjupyter                                                  # defaults
sjupyter --help                                           # options
sjupyter --time 0-5:00:00 --gpu 1                         # 5h, 1 GPU
sjupyter --qos course --part course --gpu 1               # course users
```

Wait for the Jupyter URL to appear; copy/paste it into your browser. Allow the security warning to proceed.

### Release Job Resources from Within Jupyter After Code Has Finished Running

Add at the end of your code:

```python
import os
job_cancel_str = "scancel " + os.environ['SLURM_JOBID']
os.system(job_cancel_str)
```

### Tensorboard

**No Jupyter:**
1. Run the program and generate logs in `my_log_dir`.
2. Wait for run to end.
3. SSH to the compute node.
4. `conda activate my_environment`
5. `tensorboard --bind_all --logdir=my_log_dir`
6. Wait for output. Copy/paste link to web browser.

**In Jupyter:**
1. In one of the first cells: `%load_ext tensorboard`
2. After cells generate log files: `!tensorboard --bind_all --logdir=my_log_dir`
3. Wait for output. Copy/paste link to web browser.

### Working with Notebooks

If you closed the browser tab while a cell was running, it keeps running on the cluster — but the output is lost. Workarounds: write variables/results to a file, or run the code as a Python script.

In IPython 6.0+ use `%%capture` cell magic. First line of the cell:

```python
%%capture cap_out
```

Save to variable on the last line: `var = cap_out.stdout`

Or print to file:

```python
with open('cap_output.txt', 'w') as f:
    f.write(cap_out.stdout)
```

When you reconnect, print `var` or call `cap_out.show()`.

---

## Useful SBATCH variables

### `constraint`

Select node feature such as CPU node type or GPU card type.

128-core CPU node example (does not mean 128 cores allocated to the job):

```bash
#SBATCH --constraint=cpu128
```

Available values: `cpu, gpu, cpu128, cpu256, gtx_1080, rtx_2080, rtx_3090, rtx_4090, rtx_6000, titan_rtx, tesla_p100`.

### `exclude`

Exclude nodes from allocation. Useful for interactive jobs you do not want on the same server.

```bash
#SBATCH --exclude=dt-1080-01,ise-1080-02
```

### `nodelist`

List a node to be allocated. **Beware:** if you list 2 nodes, Slurm will try to allocate both nodes together to the job.

```bash
#SBATCH --nodelist=dt-1080-01
```

---

## High Priority Jobs (Golden Tickets)

**Some** users have the right to prioritize their jobs when the resources for their job are not available. A high-priority submission may preempt another running job. Prioritized resources are **limited and shared among the group users**. If a user prioritizes a job and the prioritization rights are exhausted by group users, the job will be pending even though there may be available cluster resources.

High priority is **disabled in `main`**. Use a partition matching your group's rights. E.g. a group with only 4× 2080 GPUs can only use the `rtx2080` partition for high priority jobs.

```bash
sbatch --partition=<partition name> --qos=<high priority group name> <batch file name>
```

- `<high priority group name>` is usually your instructor's user name.
- `<partition name>` matches the QoS group: `gtx1080`, `rtx2080`, `rtx3090`, or `rtx6000`.

Example:

```bash
sbatch --partition=gtx1080 --qos=our_qos my_awesome.sbatch
```

> When no QoS is needed, do not use partitions other than `main`. When using QoS, do not use partition `main`.

## Prioritize Your Own Jobs

The `nice` parameter sets a job's priority **lower** so other jobs of yours can be prioritized over it. Higher value → lower priority. Default 0.

```bash
scontrol update JobId=<my-job-id> Nice=500
```

---

## Allocate Extra RAM/CPUs

If your job requires more than the default 24G RAM per GPU:

```bash
#SBATCH --mem=48G
```

> If you believe your job requires more than 58G please contact the IT team.

If you are NOT allocating a GPU and need more than the default CPUs:

```bash
#SBATCH --cpus-per-task=6
```

---

## Working with the Compute Node's SSD Drive

Use the compute node local drive (`/scratch`) for fast data access.

In the sbatch script:

```bash
#SBATCH --tmp=100G                          ### space on /scratch
```

Then in user code:

```bash
export SLURM_SCRATCH_DIR=/scratch/${SLURM_JOB_USER}/${SLURM_JOB_ID}

cp /storage/*.img $SLURM_SCRATCH_DIR        ### copy .img files TO local
mkdir $SLURM_SCRATCH_DIR/testtttt
...
# user code that reads/writes to $SLURM_SCRATCH_DIR/testtttt
...
cp -r $SLURM_SCRATCH_DIR $SLURM_SUBMIT_DIR  ### copy back to home
```

> When the job has finished, is canceled, or fails, **ALL data in `$SLURM_SCRATCH_DIR` is erased!** This temp folder lives only with running jobs.

---

## Sending Arguments to sbatch File

Launch with command-line arguments:

```bash
sbatch --export=ALL,var1='1',var2='hello' my_sbatch_file.sbatch
```

Inside the sbatch file, reference with `$`:

```bash
echo $var2
```

---

## Job Arrays

Run identical script with different env vars (parameter tuning, multiple seeds).

```bash
#SBATCH --array=1-10                        ### run parallel 10 times
```

Each job gets the requested resources (e.g. 6 CPUs each). The env var `SLURM_ARRAY_TASK_ID` will hold the current task id (1..10).

Change output naming so each task writes to its own file:

```bash
#SBATCH --output=file_name_%A_%a.out
```

`%a` → `SLURM_ARRAY_TASK_ID`, `%A` → master job id.

In Python:

```python
import os
jobid = os.getenv('SLURM_ARRAY_TASK_ID')
```

In R:

```r
task_id <- Sys.getenv("SLURM_ARRAY_TASK_ID")
```

Or pass as a CLI arg:

```bash
python my_code.py $SLURM_ARRAY_TASK_ID
```

### Send Name of an Input File to Each Task

For input files ending in `.txt`:

```bash
file=$(ls *.txt | sed -n ${SLURM_ARRAY_TASK_ID}p)
myscript -in $file
```

### Read a Line from an Input File for Each Task

```bash
SAMPLE_LIST=($(<input.list))
SAMPLE=${SAMPLE_LIST[${SLURM_ARRAY_TASK_ID}]}
```

### Email Notifications

Get an email per task (rather than only for the whole job):

```bash
#SBATCH --mail-type=BEGIN,END,FAIL,ARRAY_TASKS
```

### Limiting the Number of Simultaneously Running Tasks from the Job Array

Limit a 16-job array to 4 simultaneous:

```bash
#SBATCH --array=0-15%4
```

---

## Job Dependencies

Defer the start of a job based on another job's condition.

```bash
sbatch --dependency=after:<other_job_id> <sbatch_script>          ### after other_job started
sbatch --dependency=afterok:<other_job_id> <sbatch_script>        ### after other_job ends OK
sbatch --dependency=afterok:77:79 my_sbatch_script.sh             ### start after BOTH 77 and 79 finished
sbatch --dependency=singleton                                     ### begin after termination of all previously launched jobs sharing the same job name and user
```

---

## CUDA Version Selection

CUDA drivers are installed on all compute nodes. Load a specific version in your sbatch:

```bash
module load cuda/9.0
```

Available versions:

```
cuda/7.0  cuda/7.5  cuda/8.0  cuda/9.0  cuda/9.1  cuda/9.2
cuda/10.0 cuda/10.1 cuda/10.2
cuda/11.0 cuda/11.1 cuda/11.2 cuda/11.3 cuda/11.4 cuda/11.5 cuda/11.6 cuda/11.7 cuda/11.8
cuda/12.0 cuda/12.1 cuda/12.2 cuda/12.3 cuda/12.4 cuda/12.5 cuda/12.6 cuda/12.8 cuda/12.9
cuda/13.0 cuda/13.1
```

---

## IDEs

### pyCharm

Make sure you have **pyCharm Professional** installed (free for students/academy people).

Create an interactive session:
1. SSH to Slurm.
2. Launch a GPU (or CPU-only) interactive job: `sinteractive --gpu 1`. Output lists the node hostname and job id.
3. Open pyCharm → Settings → Project → Project Interpreter.
4. Top-right next to Project Interpreter: 'add interpreter' (or settings icon → 'add').
5. Choose 'On SSH' (or 'SSH Interpreter' on the left). Under 'New server configuration' fill in the **compute node's hostname** (do **not** fill in the manager node's hostname!) and your BGU user name. Click Next.
6. Accept host authenticity prompt. Enter your BGU password. Click Next.
7. If possible, choose 'System Interpreter'. In 'Interpreter:' enter the path: `/home/<your_user>/.conda/envs/<your_environment>/bin/python`.
8. Click Finish. Wait for pyCharm to upload files (status bar).
9. To avoid re-uploading on each new compute node, map the sync folder to your cluster home directory; or disable auto-sync — both in the bottom of the 'Add python interpreter' dialog.

**Show Remote File Tree Window:** `ALT+F1` → 'Remote Host'. May need: Settings → Build, Execution, Deployment → Deployment → choose the right SSH config.

#### Make pyCharm Continue Running Script When Session is Disconnected

`offline_training.py` launches another script with arguments and redirects output to `result.txt`:

```python
import os
import sys

os.system("nohup bash -c '" +
          sys.executable + " train.py --size 192 >result.txt" +
          "' &")
```

The above runs `train.py --size 192`. The `result.txt` file may be found on the compute node. After running `offline_training.py` in PyCharm, the 'Python Console' shows:

```
runfile('/tmp/pycharm_project_<some_number>/<your_offline_running_file>.py',
        wdir='/tmp/pycharm_project_<some_number>')
```

That's the path to the synced folder on the compute node. SSH to the compute node and find `result.txt` there.

> Once the job ends, that folder is **erased**!

### Visual Studio Code

Create an interactive session:
1. SSH to Slurm.
2. `sinteractive --gpu 1` (or CPU-only). Output lists the node hostname and job id.
3. Install VS Code locally with a supported OpenSSH client. Install the 'Remote — SSH' pack.
4. Install the Python package, if needed.
5. Press the green button (`><`) on the bottom-left.
6. Top-middle: choose "Remote — SSH: Connect to host…" and enter `<your_BGU_user>@<compute_node_hostname>`. **Do not fill in the manager node's hostname!!!**
7. New window opens. Enter your BGU password.
8. `Ctrl+Shift+P` → 'Python: Select Interpreter' → choose interpreter from your env (`~/.conda/envs/<environment>/bin/python`).

To enable interactive notebook-like cells: `Ctrl+Shift+P` → 'Preferences: Open Workspace Settings' → 'Python'. Scroll to 'Conda Path' and fill in:

```
/storage/modules/packages/anaconda/lib/python3.11/venv/scripts/common/activate
```

If you hit "cannot find actual path of the python script", add to `launch.json`:

```json
"cwd": "${fileDirname}"
```

#### Run/Debug with Arguments

Open the python file. Press the Debug symbol in the left ribbon. Click 'create a launch.json file'. Open `launch.json` and add (4 args example):

```json
"args": ["--arg_name1", "value_1", "--arg_name2", "value_2"]
```

Full example:

```json
"configurations": [
    {
        "name": "Python: Current File",
        "type": "python",
        "request": "launch",
        "program": "${file}",
        "console": "integratedTerminal",
        "cwd": "${fileDirname}",
        "args": ["cuda", "100", "exit"]
    }
]
```

#### Run Jupyter Notebook (avoid SSL certificate error)

1. Cogwheel → Settings → search 'cert' → tick 'Jupyter: Allow Unauthorized Remote Connection'.
2. Edit cluster file `~/.vscode/settings.json` and add: `"http.systemCertificates": true`
3. Add to end of cluster `~/.bashrc`: `export NODE_TLS_REJECT_UNAUTHORIZED='0'`

---

## Docker

Run Docker containers on the cluster using either the **preferred Apptainer** or UDOCKER.

### Apptainer

- Create an interactive job using: `/storage/interactive.sh`
- SSH to the compute node that was allocated to you.
- Download your container and create a `.sif`:
  ```bash
  apptainer build --force my_container.sif docker://my_container_page/my_container
  ```
- Run the container (last argument is the command — here, a bash shell):
  ```bash
  apptainer exec my_container.sif /bin/bash
  ```
  OR
  ```bash
  apptainer exec --nv --bind cluster_dir:container_dir my_container.sif /bin/bash
  ```
  - `--nv` gives the container access to the GPU (if allocated).
  - `--bind` binds a cluster directory to a container directory — useful for write permissions.

#### Building Images on Your Local Machine

- Build the image with Docker on your system.
- Save the image to a `.tar`: `docker save -o my-image.tar my-image:latest`
- Copy the `.tar` to the cluster.
- Run a job that builds the `.sif` image and uses it with Apptainer: `apptainer build my-image.sif docker-archive://my-image.tar`

### UDOCKER

UDOCKER must be installed in a Conda environment. UDOCKER is **not** a full Docker replacement — usage is currently **limited to pulling and running containers**. Containers should still be built using Docker and Dockerfiles.

#### Installation

(Python 3 — for Python 2 remove `python=3.8`.)

```bash
conda create -n udocker_env python=3.8
conda activate udocker_env
conda install configparser
pip install udocker
```

#### Test (tensorflow-gpu container example)

In your sbatch:

```bash
module load anaconda
source activate udocker_env
udocker pull tensorflow/tensorflow:2.8.0rc0-gpu-jupyter             # pull
udocker create --name=tf_gpu_jup28 tensorflow/tensorflow:2.8.0rc0-gpu-jupyter  # create
udocker setup --nvidia tf_gpu_jup28                                  # GPU support
udocker run tf_gpu_jup28 nvidia-smi                                  # check GPU
# mount your code dir to container's /home and run python code
udocker run -v /home/my_user/my_code_dir:/home tf_gpu_jup28 python3 /home/my_code.py
```

Useful commands:

```bash
udocker --help                  # info on commands
udocker run --help              # help for the 'run' command (others similar)
udocker ps                      # list containers
udocker images                  # list images
udocker rm <container name/id>  # remove container
udocker rmi <image id>          # remove image
```

No need to pull the image every time. No need to recreate or re-setup Nvidia for an existing container.

#### Run Jupyter Lab in Udocker

- After creating a Udocker conda env (above), copy `/storage/udocker_jup.sbatch` to your directory.
- Modify the env name and the docker image as desired.
- Run `sbatch udocker_jup.sbatch`.
- Open the output file. Grab the port number from the first lines and the token from the last lines (image download may take ~15 min for the example).
- Replace the port number of the token with the port number you grabbed.
- Replace the hostname with its IP address (`ping` the host to find it).
- Paste the modified token into your browser's address bar.

---

## Matlab

Run Matlab GUI from terminal (no sbatch needed):

```bash
module load matlab
srun --x11 --nodes=1 --mem=24G --cpus-per-task=4 --gpus=1 --partition=main matlab -nosoftwareopengl -desktop -sd ~
```

Matlab 2021A:

```bash
module load matlab/R2021A
srun --x11 --nodes=1 --mem=24G --cpus-per-task=4 --gpus=1 --partition=main --time=01:00:00 matlab -desktop -sd ~
```

> Make sure your SSH terminal supports x11 forwarding!

Headless Matlab (batch script):

```bash
srun --nodes=1 --mem=24G --cpus-per-task=4 --gpus=1 --partition=main matlab -nosplash -nodisplay -nodesktop -sd ~ -batch "my_matlab_script"
```

Headless Matlab can also run via `sbatch`.

**Cluster params:** `--nodes` (must be 1), `--mem=24G`, `--cpus-per-task`, `--gpus`, `--partition`.

**Matlab params:** `-desktop` (GUI mode), `-sd` (working directory).

In the Matlab console:

```matlab
gpuDeviceCount
feature('numcores')
```

---

## Julia

First-time install:

```bash
julia -e 'using Pkg; Pkg.add("IJulia")'
```

The Julia kernel and Julia console will be available in Jupyter Notebook.

---

## R

### Command Line

- Create an R conda env: `conda create -n r_env r-essentials r-base`
- Launch an interactive job: `sinteractive` (`sinteractive --help` for options).
- Wait for resources to be allocated.
- Copy the compute node's hostname from the script output.
- SSH to the compute node.
- `conda activate r_env`
- `R`

### R in Jupyter

Example R conda env for Jupyter:

```bash
conda create -n r_jupyter python=3.9 jupyterlab r-essentials r-base
conda activate r_jupyter
conda install -c conda-forge r-irkernel
R -e "IRkernel::installspec()"
```

In Jupyter web interface, change kernel and select "R".

### R in MS Visual Studio Code

Install the R extension. A new 'R' button appears on the left menu.

Open an `.ipynb` notebook.

For `.r` files:
- `Ctrl+,` for settings.
- Find 'R' on the left menu.
- Find 'R > Rpath: Linux'. Type the location of the R executable: `/home/<your_user_name>/.conda/envs/<your R environment>/bin/R`
- Repeat for 'R > Rterm: Linux'.

### RStudio

Run an RStudio Apptainer and connect via web browser.

- Go to your working directory.
- `cp /storage/scripts/apptainer/rstudio/* .`
- `sbatch rstudio.sbatch`
- Extract the IP and allocated port from the output: `132.72.X.Y:port-number` and paste in browser.

---

## C#

### Install In Conda Environment

```bash
conda install -c conda-forge dotnet-sdk
```

### Use

- `./interactive.sh` to allocate a compute node.
- SSH to the compute node.
- `conda activate <your dotnet environment name>`
- `dotnet new console -o myApp`
- `cd myApp`
- `dotnet run`

### Adding Packages to .Net

```bash
dotnet add package <package name>
```

### Adding Project to Solution

```bash
dotnet sln my_solution.sln add some_project.csproj
```

---

## Fiji — Image Analysis Tool

Read about Fiji at <https://fiji.sc/>.

Run Fiji on the cluster:

```bash
srun --x11 --gpus=1 --partition=gtx1080 /storage/apps/Fiji/ImageJ-linux64
```

> Make sure you use an SSH terminal that supports X11 forwarding!

---

# Appendix

## Step by Step Guide for First Use of Python and Conda

1. Make sure you are connected through VPN or from within BGU campus.
2. Download an SSH terminal — e.g. <https://mobaxterm.mobatek.net/download.html>.
3. Open the SSH terminal and start a session (port 22). Remote host: `slurm.bgu.ac.il`. Use your BGU username/password.
4. Once logged into the manager node, create your Conda env. E.g.: `conda create -n my_env python=3.10`
5. `conda activate my_env`
6. `pip install <whatever package you need>` or `conda install ...`
   - For PyTorch: `pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`
   - For Tensorflow: `pip install 'tensorflow[and-cuda]'`
7. `conda deactivate`
8. Copy the sbatch file (don't forget the dot at the end!): `cp /storage/example.sbatch .`
9. Edit with nano: `nano example.sbatch`
10. Change the job name (replace `my_job`).
11. Last lines: `source activate my_env` — replace `my_env` with your env name.
12. The very last line demonstrates running `my_code.py` with one argument.
13. Save: `Ctrl+x`, `y`, `Enter`.
14. Launch: `sbatch example.sbatch`
15. You should immediately get the job id.
16. Status: `squeue --me`
17. Under 'ST' (state): `PD` = pending, `R` = running. Output file: `less job-<job id>.out`

## Example for Creating Latest Tensorflow-gpu and Jupyter Lab Environment

To get the **latest** Tensorflow you must install on a compute node (NOT on master).

- Submit interactive job: `sinteractive --gpu 1`
- Wait for it to run, then SSH to the compute node hostname.
- Create env: `conda create -n tfgpu_jup`
- Activate: `conda activate tfgpu_jup`
- Install Tensorflow GPU: `pip install 'tensorflow[and-cuda]'`
- Install Jupyter Lab: `conda install -c conda-forge jupyterlab`
- Make env available in notebook: `python -m ipykernel install --user --name tfgpu_jup --display-name "tfgpu_jup"`
- Deactivate: `conda deactivate`
- Cancel interactive job: `scancel <job id>`
- Submit new Jupyter job: `sjupyter --gpu 1`
- Wait for resources. Copy the whole token (address `132.72.X.Y`) into your browser.
- Confirm advancing despite security warning.
- Create a new notebook.
- Select `tfgpu_jup` kernel from upper-right corner.

---

## Conda

### Viewing a list of your environments

```bash
conda env list
```

### List of all packages installed in a specific environment

```bash
conda list                  # for an active env
conda list -n <my_env>      # for an inactive env
```

### Activating / deactivating environment

```bash
source activate <my_env>
# or (depends on conda version)
conda activate <my_env>
conda deactivate
```

### Create Environment

```bash
conda create -n <my_env>

# specific python version
conda create -n <my_env> python=3.4

# with specific package (scipy)
conda create -n <my_env> scipy
# Or
conda create -n <my_env> python
conda install -n <my_env> scipy

# specific package version
conda create -n <my_env> scipy=0.15.0

# multiple packages
conda create -n <my_env> python=3.4 scipy=0.15.0 astroid babel
```

### Remove Environment

```bash
conda env remove --name myenv
```

### Update Conda

```bash
conda update conda
```

### Compare Conda Environments

A Python (2) script is in `/storage`:

```bash
python conda_compare.py <environment1> <environment2>
```

---

## Transfer Files

### To / From Your PC

You can use **WinSCP** to transfer files.

### Get a Public File

**from AWS s3:**

```bash
wget --no-check-certificate --no-proxy 'https://<your bucket name>.s3.amazonaws.com/<path and name of file>'
```

**from Google Drive:**

```bash
wget --load-cookies /tmp/cookies.txt \
  "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate \
    'https://docs.google.com/uc?export=download&id=<YOUR FILE ID>' -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=<YOUR FILE ID>"
```

`<YOUR FILE ID>` is the alphanumeric long string from the file's link in Chrome.

---

## Github

### How to Set an SSH Key to Your Account

- If you didn't generate ssh keys in your home directory:
  ```bash
  ssh-keygen -t ed25519 -C "your_email@example.com"
  ```
- When prompted to "Enter a file in which to save the key", press **Enter** for the default location.
- When prompted for passphrase, use one easy to remember (you'll need it every time you connect).
- Print the key: `cat ~/.ssh/id_ed25519.pub`
- Copy the key and paste at <https://github.com/settings/keys>. Press 'create a new ssh key' and paste.
- Test connection (passphrase required): `ssh -T git@github.com`

---

# FAQ

## Usage

**Can I SSH the cluster when I am away from university?**
Use the VPN.

**I uploaded files while logged into the manager node — can a compute node find them?**
Yes. Files were uploaded to the storage. **All** cluster nodes have access to your files there.

**I need sudo to install library X / tool Y.**
Install it in your conda env using `conda install` or `pip install`.

**How to tell which GPU was allocated for the job?**
Write `nvidia-smi -L` either in the sbatch file, or SSH to the compute node and run it there.

**Even though I installed tensorflow, it does not recognize any GPU.**
Make sure to: `pip install 'tensorflow[and-cuda]'`

**Does a Jupyter notebook keep on running when I close the browser?**
See [Working with Notebooks](#working-with-notebooks).

**When running Jupyter Lab in browser, kernel shows as disconnected.**
Try another browser or reset to factory defaults. Browser add-ons may block kernel comms.

**On Mac OS, opening Jupyter Lab on Chrome or Safari, security settings prevent the notebook from loading.**
Use Firefox or Maxthon.

**Is Git installed on the cluster?**
Yes, on the manager node.

**Why is my job pending? What's the meaning of REASON?**
- `PartitionTimeLimit` — `time` exceeds the partition's max (usually 7 days).
- `Resources` — cluster currently lacks resources.
- `Priority` — queued behind higher-priority jobs. May have exceeded your group's QoS priority resources — launch without QoS or wait.
- `QOSMaxJobsPerUserLimit` — reached max concurrent jobs for the requested partition.
- `MaxGRESPerAccount` — your high-priority job exceeds the limit of concurrent GPUs allocated to your account; waiting for golden card.

**In Python app I print runtime info but it's buffered (printed all at once).**
- `python -u my_py_app.py` (`u` = unbuffered).
- Or in sbatch: `export PYTHONUNBUFFERED=TRUE`.
- Has a perf cost — not advisable outside debugging.

**Tensorflow does not recognize GPU.**
Make sure tensorflow version supports GPU; libraries and driver versions must match:

| Version             | Python      | Compiler   | Build Tools  | CUDNN | CUDA |
|---------------------|-------------|------------|--------------|-------|------|
| tensorflow-2.15.0   | 3.9–3.11    | Clang 16.0 | Bazel 6.1.0  | 8.9   | 12.2 |
| tensorflow-2.14.0   | 3.9–3.11    | Clang 16.0 | Bazel 6.1.0  | 8.7   | 11.8 |
| tensorflow-2.13.0   | 3.8–3.11    | Clang 16.0 | Bazel 5.3.0  | 8.6   | 11.8 |
| tensorflow-2.12.0   | 3.8–3.11    | GCC 9.3.1  | Bazel 5.3.0  | 8.6   | 11.8 |
| tensorflow-2.11.0   | 3.7–3.10    | GCC 9.3.1  | Bazel 5.3.0  | 8.1   | 11.2 |
| tensorflow-2.10.0   | 3.7–3.10    | GCC 9.3.1  | Bazel 5.1.1  | 8.1   | 11.2 |
| tensorflow-2.9.0    | 3.7–3.10    | GCC 9.3.1  | Bazel 5.0.0  | 8.1   | 11.2 |
| tensorflow-2.8.0    | 3.7–3.10    | GCC 7.3.1  | Bazel 4.2.1  | 8.1   | 11.2 |
| tensorflow-2.7.0    | 3.7–3.9     | GCC 7.3.1  | Bazel 3.7.2  | 8.1   | 11.2 |
| tensorflow-2.6.0    | 3.6–3.9     | GCC 7.3.1  | Bazel 3.7.2  | 8.1   | 11.2 |
| tensorflow-2.5.0    | 3.6–3.9     | GCC 7.3.1  | Bazel 3.7.2  | 8.1   | 11.2 |
| tensorflow-2.4.0    | 3.6–3.8     | GCC 7.3.1  | Bazel 3.1.0  | 8.0   | 11.0 |
| tensorflow-2.3.0    | 3.5–3.8     | GCC 7.3.1  | Bazel 3.1.0  | 7.6   | 10.1 |
| tensorflow-2.2.0    | 3.5–3.8     | GCC 7.3.1  | Bazel 2.0.0  | 7.6   | 10.1 |
| tensorflow-2.1.0    | 2.7, 3.5–3.7| GCC 7.3.1  | Bazel 0.27.1 | 7.6   | 10.1 |
| tensorflow-2.0.0    | 2.7, 3.3–3.7| GCC 7.3.1  | Bazel 0.26.1 | 7.4   | 10.0 |
| tensorflow_gpu-1.15.0 | 2.7, 3.3–3.7 | GCC 7.3.1 | Bazel 0.26.1 | 7.4 | 10.0 |
| tensorflow_gpu-1.14.0 | 2.7, 3.3–3.7 | GCC 4.8   | Bazel 0.24.1 | 7.4 | 10.0 |

To load CUDA driver: `module load cuda/xx.x` after `module load anaconda`. See [CUDA Version Selection](#cuda-version-selection).

**My 2 simultaneous interactive jobs get the same compute node. All SSH sessions to that node show the same jobid (use that job's resources). I want one of the sessions to use the other job's resources.**
The SSH session uses the first job's resources. To connect to the second job's resources:

```bash
srun --jobid=<my-2nd-jobid> --pty bash
```

You can also run that in the VS Code terminal. To close the new shell: `exit`.

**My job requires a lot of RAM, what can I do?**
Find the cause. E.g. for image-dataset preprocessing, use pointers to images for preprocessing rather than loading them all in RAM. Example: <https://www.kaggle.com/itslek/transfer-learning-keras-flowers-sf-dl-v1>

**How to profile python memory usage?**
<https://www.pluralsight.com/blog/tutorials/how-to-profile-memory-usage-in-python>

**Using Bert consumes a lot of RAM and either OOM errors occur or a lot of RAM needs to be allocated.**
- <https://github.com/google-research/bert#out-of-memory-issues>
- <https://stackoverflow.com/questions/59617755/training-a-bert-based-model-causes-an-outofmemory-error-how-do-i-fix-this>

**I need java version 11, but `conda install openjdk` installs version 1.8.**
The following installs Java 11 in your home folder:
- Create a conda env and `pip install install-jdk==0.1.0`
- In Python:
  ```python
  import jdk
  jdk.install('11')
  ```
- Modify env vars (e.g. version 11.0.22):
  ```bash
  export JAVA_HOME="/home/<your username>/.jdk/jdk-11.0.22+7"
  export PATH=$JAVA_HOME/bin:$PATH
  ```

## Errors

**`RuntimeError: CUDA out of memory. Tried to allocate 448.00 MiB ...`** or **`Resource exhausted: OOM when allocating tensor with shape ...`**

Trying to allocate more GPU memory than available (e.g. 10.73GiB on Nvidia 2080). Reduce batch size to fit available memory.

If the issue persists, code may be grabbing more memory than you realize.

**Tensorflow:** grabs 95% of memory by default (avoids costly dynamic allocation), so allocations from another process will fail.

Configure Tensorflow to allocate growing memory (flexible, but slower) — TF1 API:
```python
config = tf.ConfigProto()
config.gpu_options.allow_growth = True
session = tf.Session(config=config, ...)
```
Or:
```python
tf.config.experimental.set_memory_growth(physical_devices[0], True)
```

To allocate a fixed fraction (e.g. 1/3) per process:
```python
gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.333)
sess = tf.Session(config=tf.ConfigProto(gpu_options=gpu_options))
```

For TF2 compatibility module: replace `tf.GPUOptions` with `tf.compat.v1.GPUOptions`, `tf.ConfigProto` with `tf.compat.v1.ConfigProto`, etc.

**pyTorch:**
- (a) Sometimes you leave a reference to a CUDA tensor — accumulates memory across iterations (see <https://github.com/pytorch/pytorch/issues/16417>).
- (b) Use `detach()` if appropriate (removes the graph if you're not using gradient descent).
- (c) Use the garbage collector and cache emptying:
  ```python
  del variables
  gc.collect()
  torch.cuda.empty_cache()
  ```

Readable summary of GPU allocation:
```python
torch.cuda.memory_summary(device=None, abbreviated=False)
```

More: <https://pytorch.org/docs/stable/notes/faq.html>

**`Got: RuntimeError: CUDA error: no kernel image is available for execution on the device…`**
CUDA code wasn't compiled for your GPU architecture. The 1080 GPU architecture is a bit outdated — don't use it for that code.

**Running Jupyter in VS Code: `Failed to start the Kernel. ... reason: self signed certificate. View Jupyter log for further details.`**
Use the settings described in [Run Jupyter Notebook](#run-jupyter-notebook-avoid-ssl-certificate-error).

**`conda install wget` then `ModuleNotFoundError: No module named wget`.**
Use `pip install wget`.

**Python wrapper of binary code installed via conda — works in Jupyter but PyCharm fails with `NotImplementedError: "..." does not appear to be installed or on the path. ...`**
With PyCharm the env var `PATH` remains unchanged (unlike Jupyter which modifies it when choosing a conda env). Modify `PATH` **before** importing the wrapper package:

```python
import os
os.environ['PATH'] = (
    '/home/<your_user>/.conda/envs/<your_env>/bin:'
    '/storage/modules/packages/anaconda3/bin:'
    '/storage/modules/bin:'
    '/storage/modules/packages/anaconda3/condabin:'
    '/usr/local/bin:/usr/bin:/usr/local/sbin:/usr/sbin:'
    '/storage/modules/packages/matlab/R2019B/bin:'
    '/home/<your_user>/.local/bin:/home/<your_user>/bin'
)
import <python wrapper package>
```

**Using DDP in PyTorch with multiple RTX6000 cards the program hangs (does not happen on 3090/4090).**
Server topology does not support P2P. Add to your sbatch (after `#SBATCH` lines):
```bash
export NCCL_P2P_DISABLE=1
```

**PyTorch: `OSError: [Errno 28] No space left on device`.**
`tmpfs` (`/dev/shm`) was full — used for temp RAM files, half the node's RAM. Either:
- limit dataset size,
- disable multiprocessing: `num_workers=0`,
- redirect data to file system temp folder: `export TMPDIR=/your/custom/temp/folder` (advised: use the scratch folder; see [Working with the Compute Node's SSD Drive](#working-with-the-compute-nodes-ssd-drive)),
- ```python
  import torch.multiprocessing as mp
  mp.set_sharing_strategy('file_system')
  ```

**GPU 3090 with tensorflow: `InternalError: CUDA runtime implicit initialization on GPU:0 failed. Status: device kernel image is invalid`.**
You need tensorflow > 2.2.

**GPU 3090 with PyTorch: `NVIDIA GeForce RTX 3090 with CUDA capability sm_86 is not compatible with the current PyTorch installation. The current PyTorch install supports CUDA capabilities sm_37 sm_50 sm_60 sm_70.`**
Pip-upgrade torch:
```bash
pip3 install torch==1.10.1+cu113 torchvision==0.11.2+cu113 torchaudio==0.10.1+cu113 -f https://download.pytorch.org/whl/cu113/torch_stable.html
```

**VSCode: `Could not establish connection to… The VS Code Server failed to start SSH`.**
SSL certificate error on the client. Make sure SSH package of VS Code is updated and follow [Run Jupyter Notebook](#run-jupyter-notebook-avoid-ssl-certificate-error).

**VSCode: windows remote host key has changed; port forwarding is disabled.** OR `Could not establish connection to "x.x.x.x": Remote host key has changed, port forwarding is disabled.` OR `the process tried to write to a nonexistent pipe`.
Remote host key does not match local saved key (e.g. the remote was reinstalled). Go to `C:\Users\<your Windows user>\.ssh\` and rename the files; Windows will recreate them.

**VSCode glibc errors when connecting to cluster.**
Versions ≥ 1.86 require advanced glibc currently unavailable on the cluster. Uninstall VSCode and install **VSCode 1.85** from <https://update.code.visualstudio.com/1.85.2/win32-x64-user/stable>. Immediately disable auto-update: File → Settings → search "update" → set "Update: Mode" to **none**.

**Cannot find kernels when running notebooks in VS Code after reinstalling VS Code.**
Profile may be corrupted. File → Preferences → Profile → Show Profile Content; inspect packages or create a new profile.

**`SBATCH --gpus=rtx_6000:2 SBATCH --nodes=1` — error: `GPU Parameter Set ! Using GPU Partition. sbatch: error: Batch job submission failed: Requested node configuration is not available`.**
System erratum. Add `SBATCH --cpus-per-gpu=8`.

**`NotImplementedError: Cannot convert a symbolic Tensor… to a numpy array`.**
Downgrade numpy: `pip install numpy==1.19.5`.

**Fiji: `srun: error: No DISPLAY variable set, cannot setup x11 forwarding.`**
You're using a terminal that does not support x11 forwarding. Use one that does (e.g. MobaXterm).

**Output file: `slurmstepd: error: _is_a_lwp: open() /proc/60830/status failed: No such file or directory`.**
Rare Slurm accounting error message — should not affect the job. Ignore it.

**`RuntimeError: CUDA error: no kernel image is available for execution on the device. CUDA kernel errors might be asynchronously reported at some other API call, so the stacktrace below might be incorrect. For debugging consider passing CUDA_LAUNCH_BLOCKING=1`.**
Incompatible PyTorch version — update.

**PyTorch: `RuntimeError: CUDA error: device-side assert triggered`.**
Run on CPU and set `CUDA_LAUNCH_BLOCKING=1` to get the exact location/nature. Usually out-of-range indexing.

**PyCharm to remote server: `FileNotFoundError: [Errno 2] No such file or directory: '/tmp/pycharm_project_xxx/Main.py'`.**
After finishing a job with PyCharm, saved data in PyCharm:
1. Tools → Deployment → Configuration → Remove All IP Cache
2. Tools → Deployment → Configuration → SSH Configuration → ⋯ → Remove All IP Cache
3. File → Invalidate Caches and Restart
4. Interpreter → Show All → Remove All IP Cache

**Python: `srun: error: ... Segmentation fault (core dumped)`.**
Conda env is corrupted. Create a new environment.

**`libstdc++.so.6: version 'GLIBCXX_3.4.26' not found`.**
If you already installed `libgcc` in your conda env (`conda install libgcc`), add right after the `#SBATCH` lines (replace `username` and `my_env`):
```bash
export LD_LIBRARY_PATH=/home/username/.conda/envs/my_env/lib:$LD_LIBRARY_PATH
```

**Java OOM errors: Java auto-sets MaxHeapSize to 32GB but the code only needs 8GB allocation.**
Set java max heap manually to less than 8GB to fit the cluster-allocated memory.
