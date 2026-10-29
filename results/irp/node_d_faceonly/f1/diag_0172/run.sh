export PYTHONPATH=/tmp/villa_head/vesuvius/src OMP_NUM_THREADS=4 CUDA_VISIBLE_DEVICES=""
PY=/workspace/vesuvius/.venv314/bin/python
declare -A CK=([rv3]=/workspace/vesuvius/checkpoints/reader/reader-v3.pth [dn]=/workspace/vesuvius/checkpoints/erwin/dense_native_016000.pth)
for v in 172raw 841raw 172to009 172to841 841to172; do for m in rv3 dn; do
  [ -f out_${v}_${m}.tif ] && continue
  t=$(date +%s); nice -n 15 $PY -m vesuvius.ink_detection.inference.infer $v.zarr ${CK[$m]} out_${v}_${m}.tif --layer-start 0 --layer-end 17 --direction both --no-compile --num-workers 2 --batch-size 4 > log_${v}_${m}.txt 2>&1
  echo "$v $m exit $? $(( $(date +%s)-t ))s"
done; done
echo ALLDONE
