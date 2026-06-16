#!/usr/bin/env bash

function _log() {
	local program
	program=${0##*/}
	local now
	now=$(date '+%Y-%m-%d %H:%M:%S.%3N')

	# If stdin is not from the terminal, consume it.
	# This prevents issues with back-to-back tees.
	# It also facilitates logging outside of a pipe.
	[[ -t 0 ]] || cat > /dev/null

	echo -e "[${now}] (${program})" "$@"

} >&2