/**
 * Checks that TeamShifts error reasons reach the shift dialogs.
 * Run: node --test src/teamshifts-adapter/getErrorMessage.test.js
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { getErrorMessage } from './index.js'

function errorResponse (body, contentType) {
	return new Response(body, { status: 400, headers: { 'Content-Type': contentType } })
}

test('reads detail and error from JSON responses', async () => {
	assert.equal(await getErrorMessage(errorResponse('{"detail": "Role capacity has been reached."}', 'application/json')), 'Role capacity has been reached.')
	assert.equal(await getErrorMessage(errorResponse('{"error": "Invalid value"}', 'application/json')), 'Invalid value')
})

test('reads plain-text error bodies', async () => {
	assert.equal(await getErrorMessage(errorResponse("'end' must be after 'start'.", 'text/html; charset=utf-8')), "'end' must be after 'start'.")
})

test('returns an empty string when there is no message to show', async () => {
	assert.equal(await getErrorMessage(errorResponse('', 'text/html')), '')
	assert.equal(await getErrorMessage(errorResponse('{"status": "error"}', 'application/json')), '')
	assert.equal(await getErrorMessage(errorResponse('<!doctype html><title>Not Found</title>', 'text/html')), '')
})
