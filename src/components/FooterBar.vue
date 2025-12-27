<script setup>

// To update the Homa version, you can update it manually in package.json or use npm version commands (e.g. npm version patch, npm version minor, npm version major)
import packageJson from '../../package.json';
const appVersion = packageJson.version

</script>

<template>
  <v-footer class="justify-end">
    <a class="text-caption opacity-60" href="https://github.com/eugeneyng/homa" target="_blank" rel="noopener">Homa</a>
    <p class="text-caption opacity-60">&nbsp;v{{ appVersion }} </p>
  </v-footer>
</template>