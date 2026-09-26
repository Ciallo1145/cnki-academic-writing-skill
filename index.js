import { fileURLToPath } from 'node:url'
import * as skillFilesystem from '@deepseek-ai/dsh-skill-filesystem'

export const name = 'cnki-academic-writing-skill'
export const inject = ['skills']

const PACKAGE_ROOT = fileURLToPath(new URL('./', import.meta.url))

export function apply(ctx) {
  ctx.plugin(skillFilesystem, {
    providerName: 'cnki-academic-writing-bundled',
    includeDefaultRoots: false,
    bundledSkillDir: PACKAGE_ROOT,
    watch: false,
  })
}
