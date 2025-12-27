<script setup>
import { ref } from "vue";

const isEditing = ref(false);
</script>

<template>
  <v-text-field
    v-if="isEditing"
    append-inner-icon="mdi-check"
    v-bind="$attrs"
    v-on:blur="isEditing = false"
    v-on:keyup.enter="isEditing = false"
    v-on:click:append-inner="isEditing = false"
    width="75vw"
  >
  </v-text-field>
  <v-card v-else v-bind="$attrs" v-on:click="isEditing = true">
    {{ $attrs.modelValue }}
  </v-card>
</template>
