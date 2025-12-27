<script setup>
import NavigationBar from '@/components/NavigationBar.vue';
import FooterBar from '@/components/FooterBar.vue';

</script>

<template>
  <v-app>
    <header>
      <NavigationBar />
    </header>
    <v-main>
      <RouterView v-bind:key="$route.fullPath" />
    </v-main>
    <footer>
      <FooterBar />
    </footer>
  </v-app>
</template>
