ENV_SCR=$(readlink -f "${BASH_SOURCE}")
TOOLS_DIR=$(dirname $(dirname "${ENV_SCR}"))
LOCAL_ROOT="${TOOLS_DIR}/riscv"

if [ -z  "$SNIPER_ROOT" ]; then
	export SNIPER_ROOT=$TOOLS_DIR
	echo "Setting SNIPER_ROOT to $TOOLS_DIR"
fi

### 0) Check Dependencies
"${SNIPER_ROOT}/tools/checkdependencies.py"
if [ $? -ne 0 ]; then
	echo "Resolve dependencies and come back!"
	exit 1
fi
"${SNIPER_ROOT}/tools/checkdependencies-riscv.sh"
if [ $? -ne 0 ]; then
	echo "Resolve dependencies and come back!"
	exit 1
fi

if [ -z  "$PIN_ROOT" ]; then
   echo "  Please set the PIN_ROOT environment variable to your copy of Pin"
   exit 1
fi

if [ -z  "$CPU2006_ROOT" ]; then
   echo "  Please set the CPU2006_ROOT environment variable to your installed copy of SPEC CPU2006 v1.2"
   exit 1
fi

export RISCV=$LOCAL_ROOT/riscv-tools/RV64G
export PATH=$RISCV/bin:$PATH
export RV8_HOME=$LOCAL_ROOT/rv8
export SPECKLE_ROOT=$LOCAL_ROOT/Speckle
export SPEC_DIR=$CPU2006_ROOT

NPROC=(`nproc --all`)

updateGitRepo() {
	URL=$1
	BRANCH=$2
	FOLDER=$3
	cd $LOCAL_ROOT
	if [ ! -d $FOLDER ]; then
		git clone -b $BRANCH $URL $FOLDER
		cd $FOLDER
		git submodule update --init --recursive
	else
		cd $FOLDER
		git pull
		git submodule update --recursive
	fi
}

### 1) Setting up pre-requisites

# 1a) Sniper
echo "Setting up Pin for Sniper..."
cd $SNIPER_ROOT
[[ ! -L "pin_kit" && ! -d "pin_kit" ]] && ln -s $PIN_ROOT pin_kit
echo "####################################################################################"

# 1b) riscv-tools - includes Spike (that support sift generation)
echo "Setting up riscv-tools..."
cd $LOCAL_ROOT

# Configure git to use https:// instead of git:// protocol (local config)
git config --local url."https://github.com/".insteadOf git://github.com/ 2>/dev/null || true

# NOTE: This uses an older 'sift' branch (2018) from nus-comparch/riscv-tools
#       which still has riscv-fesvr as a separate submodule.
#       In newer official riscv-isa-sim (2020+), fesvr has been integrated.
#       If updating to a newer version, riscv-fesvr may not be needed as a separate submodule.

if [ ! -d riscv-tools ]; then
	# Clone riscv-tools
	git clone -b sift https://github.com/nus-comparch/riscv-tools.git riscv-tools
	cd riscv-tools

	# Initialize all submodules EXCEPT riscv-gnu-toolchain to avoid old version issues
	# riscv-fesvr: Front-end server (deprecated in newer versions, integrated into riscv-isa-sim)
	git submodule update --init riscv-isa-sim riscv-opcodes riscv-openocd riscv-pk riscv-tests
else
	cd riscv-tools
	git pull
	# Update other submodules (not riscv-gnu-toolchain yet)
	# riscv-fesvr: Still needed for this older sift branch
	git submodule update --init riscv-isa-sim riscv-opcodes riscv-openocd riscv-pk riscv-tests
fi

# Now handle riscv-gnu-toolchain separately with latest tag (both new and existing cases)
echo "Setting up riscv-gnu-toolchain with latest tag..."
cd $LOCAL_ROOT/riscv-tools
git submodule update --init riscv-gnu-toolchain
cd riscv-gnu-toolchain

# Configure git to use https:// instead of git:// protocol (local config for this repo)
git config --local url."https://github.com/".insteadOf git://github.com/

git fetch --tags
GCC_TAG=2025.11.21
if [ -n "$GCC_TAG" ]; then
	echo "Checking out riscv-gnu-toolchain tag: $GCC_TAG"
	git checkout $GCC_TAG
	# NOTE: Do NOT recursively init submodules here
	# riscv-gnu-toolchain will download required components during build time
fi

cd $LOCAL_ROOT

# 1e) riscv-opcodes-latest (definition of the RISC-V Opcode)
echo "Setting up riscv-opcodes-latest..."
cd $SNIPER_ROOT/riscv
if [ ! -d riscv-opcodes-latest ]; then
    git clone https://github.com/riscv/riscv-opcodes.git riscv-opcodes-latest
else
    cd riscv-opcodes-latest
    git pull
fi

echo "####################################################################################"

# 1f) QEMU
echo "Setting up QEMU..."
QEMU_VERSION=9.2.4
QEMU_DIR=$SNIPER_ROOT/qemu-${QEMU_VERSION}
if [ ! -d "$QEMU_DIR" ]; then
	cd $SNIPER_ROOT
	echo "Downloading QEMU ${QEMU_VERSION}..."
	wget https://download.qemu.org/qemu-${QEMU_VERSION}.tar.xz
	tar xJf qemu-${QEMU_VERSION}.tar.xz
	cd $SNIPER_ROOT
else
	echo "QEMU ${QEMU_VERSION} already exists at $QEMU_DIR"
fi
export QEMU_HOME=$QEMU_DIR
export PATH=$QEMU_DIR/build:$PATH
echo "####################################################################################"

# 1c) rv8 simulator (that support sift generation)
echo "Setting up rv8 simulator..."
URL=https://github.com/nus-comparch/rv8.git
BRANCH=sift
FOLDER=rv8
updateGitRepo "$URL" "$BRANCH" "$FOLDER"
echo "####################################################################################"

# 1d) Speckle
echo "Setting up Speckle..."
URL=https://github.com/nus-comparch/Speckle.git
BRANCH=sift
FOLDER=Speckle
updateGitRepo "$URL" "$BRANCH" "$FOLDER"
echo "####################################################################################"

### 2) Compiling Binaries

# 2a) Generate RISC-V Decoder Header
echo "Generating RISC-V Decoder Header..."
cd $SNIPER_ROOT
if [ -f riscv/scripts/generate_riscv_decoder.py ] && [ -f riscv/riscv-opcodes-latest/arg_lut.csv ]; then
    echo "  Generating decoder_lib/riscv_decoder_generated.h..."
    cat riscv/riscv-opcodes-latest/extensions/rv_i \
        riscv/riscv-opcodes-latest/extensions/rv64_i \
        riscv/riscv-opcodes-latest/extensions/rv_m \
        riscv/riscv-opcodes-latest/extensions/rv64_m \
        riscv/riscv-opcodes-latest/extensions/rv_a \
        riscv/riscv-opcodes-latest/extensions/rv64_a \
        riscv/riscv-opcodes-latest/extensions/rv_f \
        riscv/riscv-opcodes-latest/extensions/rv64_f \
        riscv/riscv-opcodes-latest/extensions/rv_d \
        riscv/riscv-opcodes-latest/extensions/rv64_d \
        riscv/riscv-opcodes-latest/extensions/rv_c \
        riscv/riscv-opcodes-latest/extensions/rv64_c \
        riscv/riscv-opcodes-latest/extensions/rv64_zba \
        riscv/riscv-opcodes-latest/extensions/rv64_zbb \
        riscv/riscv-opcodes-latest/extensions/rv64_zbs \
        riscv/riscv-opcodes-latest/extensions/rv_v | \
    python3 riscv/scripts/generate_riscv_decoder.py \
        riscv/riscv-opcodes-latest/arg_lut.csv \
        /dev/stdin > \
        decoder_lib/riscv_decoder_generated.h

    if [ $? -eq 0 ]; then
        INST_COUNT=$(grep -c "rv_op_" decoder_lib/riscv_decoder_generated.h | head -1)
        echo "  ✓ Generated decoder with ~${INST_COUNT} instructions"
    else
        echo "  ✗ Decoder generation failed!"
        exit 1
    fi
else
    echo "  Warning: Decoder generation skipped (missing files)"
fi
echo "####################################################################################"

# 2b) Sniper
echo "Compiling Sniper..."
cd $SNIPER_ROOT
make # TODO: Parallel builds currently broken
if [ $? -ne 0 ]; then
   echo "Compiling Sniper failed!"
   exit 1
fi
echo "####################################################################################"

# 2c) riscv-tools (includes Spike)
echo "Building riscv-tools..."
cd $LOCAL_ROOT/riscv-tools
echo "Building RISC-V Tools with $NPROC process(es)"
./build-sift.sh $NPROC
if [ $? -ne 0 ]; then
   echo "Building riscv-tools failed!"
   exit 1
fi
echo "####################################################################################"

# # 2d) rv8
# #echo "Compiling rv8 simulator..."
# #cd $RV8_HOME
# #make test-build TEST_RV64="ARCH=rv64imafd TARGET=riscv64-unknown-elf"
# #make -j $NPROC
# #echo "####################################################################################"
#
# # 2e) Speckle - to compile and copy SPEC CPU2006 binaries
# echo "Compiling SPEC CPU2006 binaries..."
# cd $SPECKLE_ROOT
# ./gen_binaries_sift.sh --compile --copy
# echo "####################################################################################"
#
#
# # 3) Running SPEC binaries to generate SIFT traces
# echo "Running SPEC binaries on Spike simulator to generate SIFT traces..."
#
# # 3a) Spike
# ### Eg:3a-i) Using script
# cd $SPECKLE_ROOT
# # run_sift.sh assumes SPEC is already compiled and binaries copied to $SPECKLE_ROOT/riscv-spec-test
# ./run_sift.sh --benchmark 462.libquantum # running for a single benchmark
# # ./run_sift.sh --all # running for all benchmarks
# echo "####################################################################################"
#
#
# ### Eg:3a-ii) Without script
# # running individual binaries in Spike
# # cd $SPECKLE_ROOT/riscv-spec-test/456.hmmer
# # spike --sift=hmmer-1.sift pk  hmmer --fixed 0 --mean 325 --num 45000 --sd 200 --seed 0 bombesin.hmm
# # echo "####################################################################################"
#
#
# # 3b) rv8
# ### Eg:3b-i) Using script
# # cd $SPECKLE_ROOT
# # Change SIMULATOR=rv8 in run_sift.sh#7
# # run_sift.sh assumes SPEC is already compiled and binaries copied to $SPECKLE_ROOT/riscv-spec-test
# # ./run_sift.sh --benchmark 462.libquantum # running for a single benchmark
# # ./run_sift.sh --all # running for all benchmarks
# # echo "####################################################################################"
#
#
# ### Eg:3b-ii) Without script
# # running individual binaries in rv8
# # cd $SPECKLE_ROOT/riscv-spec-test/462.libquantum
# # $RV8_HOME/build/linux_x86_64/bin/rv-jit --log-sift --log-sift-filename libquantum-1.sift libquantum 33 5
# # echo "####################################################################################"
#
#
# # 4) Running SIFT traces with Sniper
# echo "Running SIFT traces with Sniper..."
# # Running the traces generated by Spike (assuming Eg:3a-i was already executed)
# cd $SPECKLE_ROOT/output/spike/462.libquantum
# $SNIPER_ROOT/run-sniper -criscv --traces=libquantum-1.sift
# echo "####################################################################################"
#
#
# # Running the traces generated by rv8 Simulator (assuming Eg:3b-ii was already executed)
# # cd $SPECKLE_ROOT/output/rv8/462.libquantum
# # $SNIPER_ROOT/run-sniper -criscv --traces=libquantum-1.sift
# # echo "####################################################################################"
#
# echo "export RISCV=$RISCV"
# echo "export PATH=$PATH"
# echo "export RV8_HOME=$RV8_HOME"
# echo "export SNIPER_ROOT=$SNIPER_ROOT"
# echo "export SPEC_DIR=$CPU2006_ROOT"
# echo "export SPECKLE_ROOT=$SPECKLE_ROOT"
#
# echo "####################################################################################"
