import { createRouter, createWebHistory } from 'vue-router'
import Upload from '../views/Upload.vue'
import MeetingList from '../views/MeetingList.vue'
import MeetingDetail from '../views/MeetingDetail.vue'

const routes = [
  {
    path: '/',
    redirect: '/meetings'
  },
  {
    path: '/upload',
    name: 'Upload',
    component: Upload
  },
  {
    path: '/meetings',
    name: 'MeetingList',
    component: MeetingList
  },
  {
    path: '/meetings/:id',
    name: 'MeetingDetail',
    component: MeetingDetail
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
